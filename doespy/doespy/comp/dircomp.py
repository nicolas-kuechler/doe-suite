import os, filecmp, io

# helper functions for comparing equality of directories
def compare_dir(d1, d2, ignore_infiles=[]):
    """Checks whether the content of the two directories is the same.

    Args:
        d1 (str): path to 1st directory
        d2 (str): path to 2nd directory
        ignore_infiles (list str, optional): list of strings to ignore for comparison within files. Defaults to [].

    Returns:
        bool: return True if directories are the same
    """
    comp = filedircmp(d1, d2)

    if comp.left_only or comp.right_only or comp.diff_files or comp.funny_files:

        if comp.diff_files:
            # for differing files, check if the only differences comes from the strings marked as ignore
            for diff_file in comp.diff_files:
                is_same, diff = _compare_files_ignore(f1=os.path.join(d1, diff_file), f2=os.path.join(d2, diff_file), ignores=ignore_infiles)

                if not is_same:
                    print(f"line diff found in {diff_file} - 1st diff line: \n   {diff[0]}vs.\n   {diff[1]}")
                    return False
            return True

        print(comp.report())
        return False

    for subdir in comp.common_dirs:
        if not compare_dir(os.path.join(d1, subdir), os.path.join(d2, subdir), ignore_infiles=ignore_infiles):
            return False
    return True


def _compare_files_ignore(f1, f2, ignores=[]):
    """Compares two files line by line for equality and
    allows to defines string sequences to ignore in the comparison.

    Args:
        f1 (str): path to file 1
        f2 (str): path to file 1
        ignores (list, optional): List of strings to ignore while doing the file comparison. Defaults to [].

    Returns:
        bool, info: True if files are equal (ignoring the strings in the list), else return False (+ first line with a diff)
    """
    SPECIAL_REPLACEMENT_MARKER = "%REPL%"

    with open(f1, "r") as file1, open(f2, "r") as file2:

        if isinstance(f1, io.TextIOBase) and isinstance(f2, io.TextIOBase):

            for line1, line2 in zip(file1, file2):
                my_line1 = line1
                my_line2 = line2
                for ignore in ignores:
                    my_line1 = my_line1.replace(ignore, SPECIAL_REPLACEMENT_MARKER)
                    my_line2 = my_line2.replace(ignore, SPECIAL_REPLACEMENT_MARKER)
                if my_line1 != my_line2:
                    return False, (line1, line2)

    return True, None

class filedircmp(filecmp.dircmp):
    def phase3(self):
        fcomp = filecmp.cmpfiles(self.left, self.right, self.common_files, shallow=False)
        self.same_files, self.diff_files, self.funny_files = fcomp