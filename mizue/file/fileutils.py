import os


class FileUtils:
    @staticmethod
    def get_files_of_type(path, file_type, recursive=False, fullpath=True):
        filelist = FileUtils.list_files(path, recursive=recursive, fullpath=fullpath)
        return [f for f in filelist if f.endswith(file_type)]

    @staticmethod
    def get_readable_file_size(size: int, suffix: str = "B"):
        for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
            if abs(size) < 1024.0:
                return "%3.2f%s%s%s" % (size, " ", unit, suffix)
            size /= 1024.0
        return "%.1f%s%s%s" % (size, " ", 'Y', suffix)

    @staticmethod
    def list_files(path, recursive=False, fullpath=True):
        if recursive:
            if not fullpath:
                filelist = FileUtils._list_files_recursively(path)
                return FileUtils._get_base_names_only(filelist)
            else:
                return FileUtils._list_files_recursively(path)
        else:
            if not fullpath:
                filelist = FileUtils._list_files_non_recursively(path)
                return FileUtils._get_base_names_only(filelist)
            else:
                return FileUtils._list_files_non_recursively(path)

    @staticmethod
    def list_folders(path, recursive=False, fullpath=True):
        if recursive:
            if not fullpath:
                folder_list = FileUtils._list_folders_recursively(path)
                return FileUtils._get_base_names_only(folder_list)
            else:
                return FileUtils._list_folders_recursively(path)
        else:
            if not fullpath:
                folder_list = FileUtils._list_folders_non_recursively(path)
                return FileUtils._get_base_names_only(folder_list)
            else:
                return FileUtils._list_folders_non_recursively(path)

    @staticmethod
    def _list_files_recursively(path):
        return [os.path.join(dp, f) for dp, dn, filenames in os.walk(path) for f in filenames]

    @staticmethod
    def _list_files_non_recursively(path):
        return [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

    @staticmethod
    def _get_base_names_only(filelist: list):
        return [os.path.basename(f) for f in filelist]

    @staticmethod
    def _list_folders_recursively(path):
        return [dp for dp, dn, filenames in os.walk(path) if dp != path]

    @staticmethod
    def _list_folders_non_recursively(path):
        return [os.path.join(path, item) for item in os.listdir(path) if os.path.isdir(os.path.join(path, item))]
