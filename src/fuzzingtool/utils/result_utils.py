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

from typing import Tuple

from ..utils.utils import get_human_length, fix_payload_to_output


class ResultUtils:
    detailed_results = False

    @staticmethod
    def get_formated_result(payload: str,
                            rtt: float,
                            length: int,
                            words: int,
                            lines: int) -> Tuple[str, str, str]:
        """Format the result into a dict of strings

        @type payload: str
        @param payload: The payload used in the request
        @type rtt: float
        @param rtt: The request and response elapsed time
        @type length: int
        @param length: The response body length in bytes
        @returns tuple[str, str, str]: The result formated with strings
        """
        length, order = get_human_length(int(length))
        if isinstance(length, float):
            length = "%.2f" % length
        return (
            f"{fix_payload_to_output(payload):<30}",
            '{:>10}'.format(rtt),
            f"{length:>7} {order}",
            '{:>6}'.format(words),
            '{:>5}'.format(lines)
        )

    @staticmethod
    def format_custom_field(custom_field, force_detailed: bool = False) -> str:
        """Format the value from key: value pair of the custom field in the result
        
        @type custom_field: Any
        @param custom_field: The value from key: value pair of the custom field in the result
        @returns str: The formated value, to string
        """
        if force_detailed or ResultUtils.detailed_results:
            if isinstance(custom_field, list):
                return ", ".join(custom_field)
        else:
            if isinstance(custom_field, list):
                return f"found {len(custom_field)} match(s)"
        return str(custom_field)
