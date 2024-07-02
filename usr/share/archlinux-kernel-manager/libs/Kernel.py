# Store kernel data from ALA, pacman sync db
import datetime
from datetime import datetime


class Kernel:
    def __init__(self, name, headers, version, size, last_modified, file_format):
        self.name = name
        self.headers = headers
        self.version = version
        self.size = size
        self.last_modified = last_modified
        self.file_format = file_format

    def __gt__(self, other):
        datetime_value_self = (
            datetime.strptime(self.last_modified, "%d-%b-%Y %H:%M")
            .replace(tzinfo=None)
            .date()
        )

        datetime_value_other = (
            datetime.strptime(other.last_modified, "%d-%b-%Y %H:%M")
            .replace(tzinfo=None)
            .date()
        )

        if datetime_value_other >= datetime_value_self:
            return datetime_value_other


class CommunityKernel:
    def __init__(self, name, headers, repository, version, build_date, install_size):
        self.name = name
        self.headers = headers
        self.repository = repository
        self.version = version
        self.build_date = build_date
        self.install_size = install_size

    def __gt__(self, other):
        if other.name > self.name:
            return other


class InstalledKernel:
    def __init__(self, name, version, date, size):
        self.name = name
        self.version = version
        self.date = date
        self.size = size
