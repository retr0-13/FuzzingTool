# Copyright (c) 2020 - present Vitor Oriel <https://github.com/VitorOriel>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from ...bases.base_scanner import BaseScanner
from ....objects.result import Result
from ....decorators.append_args import append_args
from ....interfaces.cli.cli_output import Colors, get_formated_result


class SubdomainScanner(BaseScanner):
    __author__ = ("Vitor Oriel",)

    @append_args
    def inspect_result(self, result: Result) -> None:
        """The decorator append_args will deal with the IP custom result attribute."""
        pass

    def scan(self, result: Result) -> bool:
        return True

    def cli_callback(self, result: Result) -> str:
        url, rtt, length = get_formated_result(
            result.url, result.rtt, result.length
        )
        ip = '{:>15}'.format(result.custom['ip'])
        return (
            f"{url} {Colors.GRAY}["
            f'{Colors.LIGHT_GRAY}IP{Colors.RESET} {ip}'" | "
            f"{Colors.LIGHT_GRAY}Code{Colors.RESET} {result.status} | "
            f"{Colors.LIGHT_GRAY}RTT{Colors.RESET} {rtt} | "
            f"{Colors.LIGHT_GRAY}Size{Colors.RESET} {length}{Colors.GRAY}]{Colors.RESET}"
        )
