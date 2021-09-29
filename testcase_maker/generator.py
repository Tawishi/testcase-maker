import tempfile
from pathlib import Path
from typing import List, TYPE_CHECKING

import attr
from attr.converters import optional

from testcase_maker.executor_manager import get_executor_for_script
from testcase_maker.resolver import Resolver
from testcase_maker.subtask import Subtask
from testcase_maker.executor import Executor

if TYPE_CHECKING:
    from testcase_maker.values import ValueGroup


@attr.define()
class TestcaseGenerator:
    """
    The generator class.

    Attributes:
        values ValueGroup: Structure to build the testcase on.
        output_dir Path: Folder where the generated testcase files will be saved.
        answer_script Path: Script that can solve the testcase to produce the correct stdout.
        script_executor Executor:
        stdin_filename_format str: Filename used for stdin. There is 2 placeholders: subtask name and testcase number.
        stdout_filename_format str: Filename used for stdout. There is 2 placeholders: subtask name and testcase number.
    """

    values: "ValueGroup" = attr.ib()
    output_dir: Path = attr.ib(default="./testcases/", converter=Path)
    answer_script: Path = attr.ib(default=None, converter=optional(Path))
    script_executor: "Executor" = attr.ib(default=None)
    subtasks: List[Subtask] = attr.ib(factory=list)
    stdin_filename_format: str = attr.ib(default="{}-{}.in")
    stdout_filename_format: str = attr.ib(default="{}-{}.out")

    def __attrs_post_init__(self):
        if not self.script_executor and self.answer_script:
            self.script_executor = get_executor_for_script(self.answer_script)

    def new_subtask(self, no_of_testcase: int, name: str = None) -> Subtask:
        """
        Creates a new subtask to work with.

        Args:
            no_of_testcase: The number of testcases to generate for this subtask.
            name: Name of the subtask. To be reflected in testcase filename.

        returns:
            The new subtask object.
        """
        if not name:
            name = str(len(self.subtasks) + 1)

        subtask = Subtask(name, no_of_testcase)
        self.subtasks.append(subtask)
        return subtask

    def generate(self, override: bool = False):
        """
        Generates both stdin and stdout for testcases.

        Args:
            override: Set to ``True`` if you want to override existing testcase files (if any). Defaults to ``False``.
        """
        self.generate_stdin(override)
        self.generate_stdout(override)

    def generate_stdin(self, override: bool = False):
        """
        Generates stdin for testcases.

        Args:
            override: Set to ``True`` if you want to override existing testcase files (if any). Defaults to ``False``.
        """
        self._pre_generation()

        for subtask in self.subtasks:
            for testcase_no in range(1, subtask.no_of_testcase + 1):
                print(f"Generating stdin for subtask '{subtask.name}', testcase '{testcase_no}'...")

                stdin_file = self._stdin_path(subtask.name, testcase_no)
                if stdin_file.is_file() and not override:
                    print(f"Skipped '{stdin_file}' as file already exist.")
                    continue

                resolver = Resolver(subtask.override_name_values)
                stdin = resolver.resolve(self.values)

                with open(stdin_file, "w", newline="\n") as input_buffer:
                    input_buffer.write(stdin)
                    input_buffer.write("\n")
                print(f"Saved '{stdin_file}'.")

    def generate_stdout(self, override: bool = False):
        """
        Generates stdout for testcases.

        !!! danger "Notice"
            Valid stdin files must be generated and present first.

        Args:
            override: Set to ``True`` if you want to override existing testcase files (if any). Defaults to ``False``.
        """
        self._pre_generation()

        if not self.answer_script:
            print("Unable to generate stdout as there is no answer script specified.")
            return

        for subtask in self.subtasks:
            for testcase_no in range(1, subtask.no_of_testcase + 1):
                print(f"Generating stdout for subtask '{subtask.name}', testcase '{testcase_no}'...")

                stdin_file = self._stdin_path(subtask.name, testcase_no)
                if not stdin_file.is_file():
                    print(f"Skipped as stdin '{stdin_file}' does not exist.")
                    continue
                with open(stdin_file, "r", newline="\n") as input_buffer:
                    stdin = input_buffer.read()

                stdout_file = self._stdout_path(subtask.name, testcase_no)
                if stdout_file.is_file() and not override:
                    print(f"Skipped '{stdout_file}' as file already exist.")
                    continue

                stdout = self._execute_script(stdin)
                with open(stdout_file, "w", newline="\n") as output_buffer:
                    output_buffer.write(stdout)
                print(f"Saved '{stdout_file}'")

    def validate(self):
        """
        Checks that answer script matches the stdout for the respective stdin.

        !!! danger "Notice"
            Not implemented yet.
        """
        pass

    def _pre_generation(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if len(self.subtasks) < 1:
            self.new_subtask(5)

    def _stdin_path(self, subtask_name: str, testcase_no: int):
        return self.output_dir.joinpath(self.stdin_filename_format.format(subtask_name, testcase_no))

    def _stdout_path(self, subtask_name: str, testcase_no: int):
        return self.output_dir.joinpath(self.stdout_filename_format.format(subtask_name, testcase_no))

    def _execute_script(self, stdin: str) -> str:
        with tempfile.TemporaryDirectory() as tmpdir:
            exec_filename = self.script_executor.compile(tmpdir, self.answer_script)
            stdout = self.script_executor.execute(exec_filename, stdin).decode("UTF-8")
        return stdout
