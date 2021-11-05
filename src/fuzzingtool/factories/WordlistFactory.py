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

from typing import List

from .BaseFactories import BaseWordlistFactory
from .PluginFactory import PluginFactory
from ..utils.http_utils import get_host, get_pure_url
from ..conn.requests.Request import Request
from ..core.defaults.wordlists import ListWordlist, FileWordlist
from ..exceptions.main_exceptions import InvalidPluginName, MissingParameter


class WordlistFactory(BaseWordlistFactory):
    def creator(name: str, params: str, requester: Request) -> List[str]:
        try:
            Wordlist = PluginFactory.class_creator(name, 'wordlists')
            if (not params and requester and
                    Wordlist.__params__['metavar'] in
                    ["TARGET_HOST", "TARGET_URL"]):
                if "TARGET_HOST" in Wordlist.__params__['metavar']:
                    params = get_host(get_pure_url(requester.get_url()))
                if "TARGET_URL" in Wordlist.__params__['metavar']:
                    params = get_pure_url(requester.get_url())
            wordlist = PluginFactory.object_creator(name, 'wordlists', params)
        except InvalidPluginName:
            try:
                if name.startswith('[') and name.endswith(']'):
                    wordlist = ListWordlist(name)
                else:
                    # For default, read the wordlist from a file
                    wordlist = FileWordlist(name)
            except MissingParameter as e:
                raise Exception(f"Missing parameter: {str(e)}")
        if len(wordlist) == 0:
            raise Exception("The generated wordlist is empty")
        return wordlist
