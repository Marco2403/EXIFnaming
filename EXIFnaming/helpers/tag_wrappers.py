import functools
import re
from collections import OrderedDict

from EXIFnaming.helpers.settings import hdr_program, panorama_program


class Location:
    def __init__(self, country="", region="", city="", location=""):
        self.country = country
        self.region = region
        self.city = city
        self.location = location

    def update(self, data: {}):
        if data['country']: self.country = data['country']
        if data['region']: self.region = data['region']
        if data['city']: self.city = data['city']
        if data['location']: self.location = data['location']

    def toTagDict(self) -> dict:
        loc_tags = [self.country, self.city, self.location]
        return {'Country': self.country, 'State': self.country, 'City': self.city, 'Location': self.location,
                'Keywords': loc_tags, 'Subject': loc_tags,
                'LocationCreatedCountryName': self.country, 'LocationCreatedProvinceState': self.region,
                'LocationCreatedCity': self.city, 'LocationCreatedSublocation': self.location}

    def __str__(self):
        out = ""
        if self.country: out += self.country
        if self.region: out += ", " + self.region
        if self.city: out += ", " + self.city
        if self.location: out += ", " + self.location
        return out


class FileMetaData:

    def __init__(self, directory, filename):
        self.directory = directory
        self.filename = filename
        self.title = ""
        self.tags = []
        self.descriptions = []
        self.description = OrderedDict()
        self.location = Location()
        regex = r"^([-\w]+)_([0-9]+)[A-Z0-9]*"
        match = re.search(regex, filename)
        if match:
            self.main_name = match.group(1)
            self.counter = int(match.group(2))
        else:
            print(filename, 'does not match ', regex)

    def update(self, data: dict):
        def not_match_entry(key: str, func):
            return key in data and data[key] and not func(data[key])

        if not_match_entry('directory', lambda value: value in self.directory):
            return
        if not_match_entry('main_name', lambda value: value == self.main_name):
            return
        if not_match_entry('first', lambda value: int(value) <= self.counter):
            return
        if not_match_entry('last', lambda value: self.counter <= int(value)):
            return

        self.title = data['title']
        self.tags += data['tags'].split(', ')
        self.descriptions.append(data['description'])
        self.location.update(data)
        set_path(self.description, ["Location"], str(self.location))

    def update_processing(self, data: dict):
        def not_match_entry(key: str, func):
            return key in data and data[key] and not func(data[key])

        def set_keys(path: [], keys: list):
            for key in keys:
                set_path(self.description, path + [key], data[key])

        def filter_key(key_part: str):
            return [key for key in data if key_part in key and data[key]]

        if not_match_entry('directory', lambda value: value in self.directory):
            return
        if not_match_entry('filename_part', lambda value: value in self.filename):
            return

        self.tags += [tag for tag in data['tags'].split(', ') if tag]
        hdr_keys = filter_key("HDR")
        tm_keys = filter_key("TM")
        pano_keys = filter_key("PANO")
        known_keys = ['directory', 'filename_part', 'tags'] + hdr_keys + tm_keys + pano_keys
        other_keys = [key for key in data if not key in known_keys and data[key]]
        if hdr_keys:
            set_path(self.description, ["Processing", "HDR", "program"], hdr_program)
            set_keys(["Processing", "HDR", "HDR-setting"], hdr_keys)
        if tm_keys:
            set_path(self.description, ["Processing", "HDR", "program"], hdr_program)
            set_keys(["Processing", "HDR", "HDR-Tonemapping"], tm_keys)
        if pano_keys:
            set_path(self.description, ["Processing", "Panorama", "program"], panorama_program)
            set_keys(["Processing", "Panorama"], pano_keys)
        if other_keys:
            print(other_keys)
            set_keys(["Processing", "misc"], other_keys)

    def toTagDict(self) -> dict:
        if not self.title:
            self.title = functools.reduce(lambda title, tag: title + ", " + tag, self.tags, "").strip(", ")

        description_formated = format_as_tree(self.description)
        if description_formated:
            self.descriptions.append(description_formated)
        full_description = functools.reduce(lambda description, entry: description + "\n\n" + entry, self.descriptions,
                                            "").strip("\n\n")
        tagDict = {'Label': self.filename, 'title': self.title, 'Keywords': self.tags, 'Subject': self.tags,
                   'ImageDescription': full_description, 'XPComment': full_description,
                   'Identifier': self.filename}
        loc_Dict = self.location.toTagDict()
        for key in loc_Dict:
            if key in tagDict:
                tagDict[key] += loc_Dict[key]
            else:
                tagDict[key] = loc_Dict[key]
        return tagDict

    def __str__(self):
        return "FileMetaData(" + self.title + " " + str(self.tags) + " " + str(self.descriptions) + " " + str(
            self.location) + ")"


def format_as_tree(data: dict) -> str:
    def indent(string: str) -> str:
        return indented_newline + string.replace("\n", indented_newline)

    out = ""
    indented_newline = "\n-" + " " * 3
    for key in data:
        if not data[key]:
            continue
        if type(data[key]) == str:
            value = data[key]
            if "\n" in value: value = indent(value)
        else:
            value = format_as_tree(data[key])
            value = indent(value)
        out += key + ": " + value + "\n"
    out = out.strip(indented_newline)
    return out


def set_path(data: dict, path, value=None):
    sub_data = data
    for key in path[:-1]:
        if not key in sub_data:
            sub_data[key] = OrderedDict()
        sub_data = sub_data[key]
    if value:
        sub_data[path[-1]] = value
    elif not path[-1] in sub_data:
        sub_data[path[-1]] = OrderedDict()
