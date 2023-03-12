import os

from ruamel.yaml.main import compose_all
from ruamel.yaml.nodes import (
    MappingNode,
    SequenceNode,
    ScalarNode,
)
from docutils.statemachine import ViewList
from docutils.parsers.rst import Directive
from docutils import nodes
from sphinx.util import logging
from sphinx.util.docutils import switch_source_input
from sphinx.errors import ExtensionError


logger = logging.getLogger(__name__)

#class TreeNode:
#    def __init__(self, value, comments, parent=None):
#        self.value = value
#        self.parent = parent
#        self.children = []
#        self.comments = comments
#        if value is None:
#            self.comment = None
#        else:
#            # Flow-style entries may attempt to incorrectly reuse comments
#            self.comment = self.comments.pop(value.start_mark.line + 1, None)
#
#    def add_child(self, value):
#        node = TreeNode(value, self.comments, self)
#        self.children.append(node)
#        return node
#
#    def remove_child(self):
#        return self.children.pop(0)


class AutoYAMLException(ExtensionError):

    category = "AutoYAML error"


class AutoYAMLDirective(Directive):

    required_arguments = 1

    def run(self):

        self.config = self.state.document.settings.env.config




        self.env = self.state.document.settings.env
        self.record_dependencies = self.state.document.settings.record_dependencies
        output_nodes = []
        location = os.path.normpath(
            os.path.join(
                self.env.srcdir, self.config.myautoyaml_root + "/" + self.arguments[0]
            )
        )

        if os.path.isfile(location):
            logger.debug("[autoyaml] parsing file: %s", location)
            #try:
            out = self._parse_file(location)
            output_nodes.extend(out)
            print(f"PARSED FILE!!! {location}:   {out}")
            #except Exception as e:
            #    raise AutoYAMLException(
            #        "Failed to parse YAML file: %s" % (location)
            #    ) from e
        else:
            raise AutoYAMLException(
                '%s:%s: location "%s" is not a file.'
                % (
                    self.env.doc2path(self.env.docname, None),
                    self.content_offset - 1,
                    location,
                )
            )
        self.record_dependencies.add(location)
        return output_nodes

    def _get_comments(self, source, source_file):
        comments = {}
        in_docstring = False
        for linenum, line in enumerate(source.splitlines(), start=1):
            line = line.lstrip()
            if line.startswith(self.config.myautoyaml_doc_delimiter):
                in_docstring = True
                comment = ViewList()
            elif line.startswith(self.config.myautoyaml_comment) and in_docstring:
                line = line[len(self.config.myautoyaml_comment) :]
                # strip preceding whitespace
                if line and line[0] == " ":
                    line = line[1:]
                comment.append(line, source_file, linenum)
            elif in_docstring:
                comments[linenum] = comment
                in_docstring = False
        return comments




    def _parse_file(self, source_file):
        with open(source_file, "r") as f:
            source = f.read()
        comments = self._get_comments(source, source_file)


        for num, lines in comments.items():

            for line in lines:
                print(f"LINE={num}     line={line}")

        print(f"COMMENTSS={type(comments)}")


        # TODO [nku] remove the part below and instead output the identified commands in the proper format
        # can also consider: https://github.com/w-vi/sphinxcontrib-cmtinc/blob/master/sphinxcontrib/cmtinc.py

        #for doc in compose_all(source):
        #    parsed_doc = self._parse_document(doc, comments)
        #    print(f"  parsed doc={parsed_doc}")
        #    docs = self._generate_documentation(parsed_doc)
        #    print(f"  docs={type(docs)}: {docs}")
#
        #    if docs is not None:
        #        yield docs


def setup(app):
    app.add_directive("myautoyaml", AutoYAMLDirective)
    app.add_config_value("myautoyaml_root", "..", "env")
    app.add_config_value("myautoyaml_doc_delimiter", "###", "env")
    app.add_config_value("myautoyaml_comment", "#", "env")
    app.add_config_value("myautoyaml_level", 1, "env")