from typing import List, Union, TYPE_CHECKING

import attr

from testcase_maker.value import Value
from testcase_maker.values import Constant, LoopValue

if TYPE_CHECKING:
    from testcase_maker.resolver import Resolver


@attr.define()
class ValueGroup(Value):
    values: List[Value] = attr.ib(factory=list)

    def add(self, value: Value):
        self.values.append(value)

    def space(self):
        self.add(Constant(" "))

    def newline(self):
        self.add(Constant("\n"))

    def repeat(self, value: "Value", amount: Union[Value, int], delimiter: str):
        self.add(LoopValue(value, amount, delimiter))

    def generate(self, resolver: "Resolver") -> str:
        return "".join([str(resolver.resolve(value)) for value in self.values])
