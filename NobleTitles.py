from gramps.gen.lib import Person
from gramps.gen.plug.report import (MenuReportOptions, Report, stdoptions, utils)
from gramps.gen.plug.menu import (PersonOption, PersonListOption, BooleanOption, ColorOption)
from gramps.gen.lib import (EventType, AttributeType)
from gramps.gen.utils.db import (get_birth_or_fallback, get_death_or_fallback)
from gramps.gen.display.place import displayer as place_displayer
from gramps.gen.datehandler import parser
from gramps.gen.utils.symbols import Symbols
from gramps.gen.utils.file import media_path_full
from gramps.gen.utils.thumbnails import get_thumbnail_path

class NobleTitlesOptions(MenuReportOptions):

    def __init__(self, name, dbase):
        MenuReportOptions.__init__(self, name, dbase)

    def add_menu_options(self, menu):
        person_list = PersonListOption('People of interest')
        menu.add_option('People of Interest', 'gidlist', person_list)

        withparents = BooleanOption(('Include ancestors'), False)
        menu.add_option('People of Interest', 'withparents', withparents)

        withchildren = BooleanOption(('Include descendents'), False)
        menu.add_option('People of Interest', 'withchildren', withchildren)

        withspouses = BooleanOption(('Include descendent spouses'), False)
        menu.add_option('People of Interest', 'withspouses', withspouses)

        color_males = ColorOption('Males', '#e0e0ff')
        color_males.set_help('The color to use to display men')
        menu.add_option('Report Options', 'colormales', color_males)

        color_females = ColorOption('Females', '#ffe0e0')
        color_females.set_help('The color to use to display women')
        menu.add_option('Report Options', 'colorfemales', color_females)

        color_unknown = ColorOption('Unknown', '#e0e0e0')
        color_unknown.set_help('The color to use when the gender is unknown')
        menu.add_option('Report Options', 'colorunknown', color_unknown)

        locale_opt = stdoptions.add_localization_option(menu, 'Report Options')
        stdoptions.add_date_format_option(menu, 'Report Options', locale_opt)
        stdoptions.add_name_format_option(menu, 'Report Options')

class NobleTitles(Report):

    def __init__(self, database, options, user):
        Report.__init__(self, database, options, user)

        self.set_locale(options.menu.get_option_by_name('trans').get_value())
        stdoptions.run_date_format_option(self, options.menu)
        stdoptions.run_name_format_option(self, options.menu)

        self.database = database

        self._gidlist = options.menu.get_option_by_name('gidlist').get_value().split()
        self._withparents = options.menu.get_option_by_name('withparents').get_value()
        self._withchildren = options.menu.get_option_by_name('withchildren').get_value()
        self._withspouses = options.menu.get_option_by_name('withspouses').get_value()

        self.fillcolor = {
            Person.MALE:    options.menu.get_option_by_name('colormales').get_value(),
            Person.FEMALE:  options.menu.get_option_by_name('colorfemales').get_value(),
            Person.UNKNOWN: options.menu.get_option_by_name('colorunknown').get_value()
        }

        symbols = Symbols()
        self.symbols = {
            'birth': symbols.get_symbol_for_string(symbols.SYMBOL_BIRTH),
            'death': symbols.get_death_symbol_for_char(symbols.DEATH_SYMBOL_LATIN_CROSS)
        }

    def begin_report(self):
        self._people = set()
        self._families = set()

        for gid in self._gidlist:
            person = self.database.get_person_from_gramps_id(gid)

            if self._withchildren:
                self.add_children(person)

            if self._withparents:
                self.add_parents(person)

    def write_report(self):
        self.write_people()
        self.write_families()

    def add_children(self, person):
        self._people.add(person.get_handle())

        for family_handle in person.get_family_handle_list():
            self._families.add(family_handle)

            family = self.database.get_family_from_handle(family_handle)
            for childref in family.get_child_ref_list():
                child = self.database.get_person_from_handle(childref.ref)
                self.add_children(child)

            if self._withspouses:
                spouse_handle = utils.find_spouse(person, family)
                if spouse_handle:
                    self._people.add(spouse_handle)

    def add_parents(self, person):
        self._people.add(person.get_handle())

        for family_handle in person.get_parent_family_handle_list():
            self._families.add(family_handle)

            family = self.database.get_family_from_handle(family_handle)

            father_handle = family.get_father_handle()
            if father_handle:
                father = self.database.get_person_from_handle(father_handle)
                self.add_parents(father)

            mother_handle = family.get_mother_handle()
            if mother_handle:
                mother = self.database.get_person_from_handle(mother_handle)
                self.add_parents(mother)

    def write_families(self):
        for handle in self._families:
            family = self.database.get_family_from_handle(handle)

            self.doc.add_node(node_id=family.get_gramps_id(),
                              label='family',
                              shape='ellipse',
                              color='',
                              style='solid,filled',
                              fillcolor='#ffffe0',
                              htmloutput=False)

            self.doc.start_subgraph(family.get_gramps_id())

            father_handle = family.get_father_handle()
            if father_handle:
                if father_handle in self._people:
                    father = self.database.get_person_from_handle(father_handle)
                    self.doc.add_link(id1=father.get_gramps_id(),
                                      id2=family.get_gramps_id(),
                                      style='',
                                      head='none',
                                      tail='none',
                                      comment='')

            mother_handle = family.get_mother_handle()
            if mother_handle:
                if mother_handle in self._people:
                    mother = self.database.get_person_from_handle(mother_handle)
                    self.doc.add_link(id1=mother.get_gramps_id(),
                                      id2=family.get_gramps_id(),
                                      style='',
                                      head='none',
                                      tail='none',
                                      comment='')

            self.doc.end_subgraph()

            for childref in family.get_child_ref_list():
                if childref.ref in self._people:
                    child = self.database.get_person_from_handle(childref.ref)
                    self.doc.add_link(id1=family.get_gramps_id(),
                                      id2=child.get_gramps_id(),
                                      style='',
                                      head='none',
                                      tail='none',
                                      comment='')

    def write_people(self):
        for handle in self._people:
            person = self.database.get_person_from_handle(handle)

            newline = '<br/>'
            label   = '<table border="0" cellspacing="2" cellpadding="0" cellborder="0"><tr><td>'

            media_list = person.get_media_list()
            if len(media_list) > 0:
                media_handle = media_list[0].get_reference_handle()
                media = self.database.get_media_from_handle(media_handle)
                media_mime_type = media.get_mime_type()
                if media_mime_type[0:5] == "image":
                    image_path = get_thumbnail_path(media_path_full(self.database, media.get_path()),
                                                    rectangle=media_list[0].get_rectangle())
                    if image_path:
                        label += '<img src="%s"/></td><td>' % image_path

            label += self._name_display.display(person)

            birth = get_birth_or_fallback(self.database, person)
            if birth:
                label += '%s%s %s %s' % (newline,
                                         self.symbols['birth'],
                                         self._get_date(birth.get_date_object()),
                                         place_displayer.display_event(self.database, birth))

            death = get_death_or_fallback(self.database, person)
            if death:
                label += '%s%s %s %s' % (newline,
                                         self.symbols['death'],
                                         self._get_date(death.get_date_object()),
                                         place_displayer.display_event(self.database, death))

            for event_ref in person.get_primary_event_ref_list():
                event = self.database.get_event_from_handle(event_ref.ref)
                if (event and event.get_type() == EventType.NOB_TITLE):
                    title = event.get_description()

                    for attribute in event_ref.get_attribute_list():
                        if attribute.get_type() == AttributeType.TIME:
                            title += ' %s' % self._get_date(parser.parse(attribute.get_value()))

                    label += '%s%s' % (newline, title)

            label += '</td></tr></table>'

            self.doc.add_node(node_id=person.gramps_id,
                              label=label,
                              shape='box',
                              color='',
                              style='solid,filled',
                              fillcolor=self.fillcolor[person.get_gender()],
                              htmloutput=True)
