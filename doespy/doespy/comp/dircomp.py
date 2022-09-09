import os
import filecmp
import re


# helper functions for comparing equality of directories
def compare_dir(d1, d2, ignore_infiles=[], ignore_files=[]):
    """Checks whether the content of the two directories is the same.

    Args:
        d1 (str): path to 1st directory
        d2 (str): path to 2nd directory
        ignore_infiles (list str, optional): list of regex patterns to
                   ignore for comparison within files. Defaults to [].

    Returns:
        bool: return True if directories are the same
    """

    comp = filedircmp(d1, d2, ignore=[".gitkeep"] + ignore_files)

    if comp.diff_files:
        # for differing files, check if the only differences comes
        # from the strings marked as ignore
        for diff_file in comp.diff_files:
            if diff_file not in ignore_files:
                is_same, diff = _compare_files_ignore(
                    f1=os.path.join(d1, diff_file),
                    f2=os.path.join(d2, diff_file),
                    ignores=ignore_infiles,
                )

                if not is_same:
                    print(
                        f"line diff found in {diff_file} ",
                        f"- 1st diff line: \n   {diff[0]}vs.\n   {diff[1]}"
                    )
                    return False

    if comp.left_only or comp.right_only or comp.funny_files:

        print(comp.report())
        return False

    for subdir in comp.common_dirs:
        if not compare_dir(
            os.path.join(d1, subdir),
            os.path.join(d2, subdir),
            ignore_infiles=ignore_infiles,
            ignore_files=ignore_files,
        ):
            return False
    return True


def _compare_files_ignore(f1, f2, ignores=[]):
    """Compares two files line by line for equality and
    allows to defines string sequences to ignore in the comparison.

    Args:
        f1 (str): path to file 1
        f2 (str): path to file 1
        ignores (list, optional): List of regex patterns to ignore while
                                doing the file comparison. Defaults to [].

    Returns:
        bool, info: True if files are equal (ignoring the strings in the list),
                    else return False (+ first line with a diff)
    """
    SPECIAL_REPLACEMENT_MARKER = "%REPL%"

    try:
        with open(f1, "r") as file1, open(f2, "r") as file2:

            for line1, line2 in zip(file1, file2):
                my_line1 = line1
                my_line2 = line2

                for ignore in ignores:
                    my_line1 = re.sub(ignore, SPECIAL_REPLACEMENT_MARKER, my_line1)
                    my_line2 = re.sub(ignore, SPECIAL_REPLACEMENT_MARKER, my_line2)

                if my_line1 != my_line2:
                    return False, (line1, line2)

    except UnicodeDecodeError:
        pass  # skip non-text file

    return True, None


class filedircmp(filecmp.dircmp):
    def __init__(self, a, b, ignore=None, hide=None):
        super().__init__(a, b, ignore, hide)

        # need to override them specifically because fielcmp.dircmp
        # does not respect the regular override
        self.methodmap["same_files"] = self.myphase3
        self.methodmap["diff_files"] = self.myphase3
        self.methodmap["funny_files"] = self.myphase3

    def myphase3(self, s):
        fcomp = filecmp.cmpfiles(
            self.left, self.right, self.common_files, shallow=False
        )
        self.same_files, self.diff_files, self.funny_files = fcomp
