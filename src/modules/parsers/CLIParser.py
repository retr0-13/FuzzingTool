## FuzzingTool
# 
# Authors:
#    Vitor Oriel C N Borges <https://github.com/VitorOriel>
# License: MIT (LICENSE.md)
#    Copyright (c) 2021 Vitor Oriel
#    Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#    The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
## https://github.com/NESCAU-UFLA/FuzzingTool

from ..core.Fuzzer import Fuzzer
from ..core.Payloader import Payloader
from ..core.scanners import *
from ..conn.Request import Request
from ..IO.OutputHandler import outputHandler as oh
from ..IO.FileHandler import fileHandler as fh

from collections import deque

class CLIParser:
    """Class that handle with the sys argument parsing"""
    def __init__(self, argv: list):
        """Class constructor

        @type argv: list
        @param argv: The system arguments list
        """
        self.__argv = argv

    def getUrl(self):
        """Get the target URL

        @returns str: The target URL
        """
        try:
            return self.__argv[self.__argv.index('-u')+1]
        except ValueError:
            oh.errorBox("An URL is needed to make the fuzzing.")

    def getDefaultRequest(self):
        """Get request headers and data, by raw file or cli input

        @returns tuple(str, str, dict, dict): The default parameters of the requests
        """
        if '-r' in self.__argv:
            url, method, data, httpHeader = self.__getRequestFromRawHttp()
        else:
            url, method, data = self.__getRequestFromArgs()
            httpHeader = {}
        requestData = self.__getRequestData(data)
        return (url, method, requestData, httpHeader)

    def getWordlistFile(self):
        """Get the fuzzing wordlist filename from -f argument
           If the argument -f doesn't exists, or the file couldn't be open, an error is thrown and the application exits
        """
        try:
            wordlistFileName = self.__argv[self.__argv.index('-f')+1]
            fh.openWordlist(wordlistFileName)
        except ValueError:
            oh.errorBox("An file is needed to make the fuzzing")

    def checkCookie(self, requester: Request):
        """Check if the --cookie argument is present, and set the value into the requester

        @type requester: Request
        @param requester: The object responsible to handle the requests
        """
        if '--cookie' in self.__argv:
            cookie = self.__argv[self.__argv.index('--cookie')+1]
            requester.setHeaderContent('Cookie', cookie)
            oh.infoBox(f"Set cookie: {cookie}")

    def checkProxy(self, requester: Request):
        """Check if the --proxy argument is present, and set the value into the requester

        @type requester: Request
        @param requester: The object responsible to handle the requests
        """
        if '--proxy' in self.__argv:
            proxy = self.__argv[self.__argv.index('--proxy')+1]
            requester.setProxy({
                'http': 'http://'+proxy,
                'https': 'https://'+proxy
            })
            oh.infoBox(f"Set proxy: {proxy}")

    def checkProxies(self, requester: Request):
        """Check if the --proxies argument is present, and open a file
        
        @type requester: Request
        @param requester: The object responsible to handle the requests
        """
        if '--proxies' in self.__argv:
            proxiesFileName = self.__argv[self.__argv.index('--proxies')+1]
            oh.infoBox(f"Loading proxies from file '{proxiesFileName}' ...")
            requester.setProxyList(fh.readProxies(proxiesFileName))

    def checkTimeout(self, requester: Request):
        """Check if the --timeout argument is present, and set the request timeout

        @type requester: Request
        @param requester: The object responsible to handle the requests
        """
        if '--timeout' in self.__argv:
            timeout = self.__argv[self.__argv.index('--timeout')+1]
            requester.setTimeout(int(timeout))
            oh.infoBox(f"Set request timeout: {timeout} seconds")

    def checkUnfollowRedirects(self, requester: Request):
        """Check if the --follow-redirects argument is present, and set the follow redirects flag

        @type requester: Request
        @param requester: The object responsible to handle the requests
        """
        if '--unfollow-redirects' in self.__argv:
            requester.setFollowRedirects(False)

    def checkDelay(self, fuzzer: Fuzzer):
        """Check if the --delay argument is present, and set the value into the fuzzer

        @type fuzzer: Fuzzer
        @param fuzzer: The Fuzzer object
        """
        if '--delay' in self.__argv:
            delay = self.__argv[self.__argv.index('--delay')+1]
            fuzzer.setDelay(float(delay))
            oh.infoBox(f"Set delay: {delay} second(s)")

    def checkVerboseMode(self, fuzzer: Fuzzer):
        """Check if the -V or --verbose argument is present, and set the verbose mode

        @type fuzzer: Fuzzer
        @param fuzzer: The Fuzzer object
        """
        if '-V' in self.__argv or '-V1' in self.__argv:
            fuzzer.setVerboseMode([True, False])
        elif '-V2' in self.__argv:
            fuzzer.setVerboseMode([True, True])

    def checkNumThreads(self, fuzzer: Fuzzer):
        """Check if the -t argument is present, and set the number of threads in the fuzzer

        @type fuzzer: Fuzzer
        @param fuzzer: The Fuzzer object
        """
        if '-t' in self.__argv:
            numThreads = self.__argv[self.__argv.index('-t')+1]
            fuzzer.setNumThreads(int(numThreads))
            oh.infoBox(f"Set number of threads: {numThreads} thread(s)")

    def checkPrefixAndSuffix(self, payloader: Payloader):
        """Check if the --prefix argument is present, and set the prefix into request parser
           Check if the --suffix argument is present, and set the suffix into request parser
        
        @type payloader: Payloader
        @param payloader: The object responsible to handle with the payloads
        """
        if '--prefix' in self.__argv:
            prefix = self.__argv[self.__argv.index('--prefix')+1]
            if ',' in prefix:
                prefixes = prefix.split(',')
            else:
                prefixes = [prefix]
            payloader.setPrefix(prefixes)
            oh.infoBox(f"Set prefix: {str(prefixes)}")
        if '--suffix' in self.__argv:
            suffix = self.__argv[self.__argv.index('--suffix')+1]
            if ',' in suffix:
                suffixes = suffix.split(',')
            else:
                suffixes = [suffix]
            payloader.setSuffix(suffixes)
            oh.infoBox(f"Set suffix: {str(suffixes)}")

    def checkCase(self, payloader: Payloader):
        """Check if the --upper argument is present, and set the uppercase flag
           Check if the --lower argument is present, and set the lowercase flag
           Check if the --capitalize argument is present, and set the capitalize flag
        
        @type payloader: Payloader
        @param payloader: The object responsible to handle with the payloads
        """
        if '--lower' in self.__argv:
            payloader.setLowercase(True)
            oh.infoBox("Set payload case: lowercase")
        elif '--upper' in self.__argv:
            payloader.setUppecase(True)
            oh.infoBox("Set payload case: uppercase")
        elif '--capitalize' in self.__argv:
            payloader.setCapitalize(True)
            oh.infoBox("Set payload case: capitalize")

    def checkReporter(self, requester: Request):
        """Check if the -o argument is present, and set the report data (name and type)
        
        @type requester: Request
        @param requester: The object responsible to handle the requests
        """
        targetUrl = requester.getParser().getTargetUrl(requester.getUrlDict())
        host = requester.getParser().getHost(targetUrl)
        if '-o' in self.__argv:
            report = self.__argv[self.__argv.index('-o')+1]
            if '.' in report:
                reportName, reportType = report.split('.')
            else:
                reportType = report
                reportName = ''
            if reportType not in ['txt', 'csv', 'json']:
                oh.errorBox(f"Unsupported report format for {reportType}! Accepts: txt, csv and json")
            oh.infoBox(f"Set report: {report}")
        else:
            reportType = 'txt'
            reportName = ''
        fh.setReport({
            'Type': reportType,
            'Name': reportName,
            'Host': host
        })

    def checkScanner(self, fuzzer: Fuzzer):
        if '--scanner' in self.__argv:
            scanner = self.__argv[self.__argv.index('--scanner')+1]
            if 'reflected' in scanner:
                from ..core.scanners.custom.ReflectedScanner import ReflectedScanner
                fuzzer.setScanner(ReflectedScanner())
            else:
                oh.errorBox(f"Scanner {scanner} not available!")
            oh.infoBox(f"Set scanner: {scanner}")

    def checkMatcher(self, matcher: Matcher):
        """Check if the --allowed-status argument is present, and set the alllowed status codes used in the Matcher

        @type matcher: Matcher
        @param matcher: The matcher object
        """
        if '-Xc' in self.__argv:
            allowedStatus = self.__argv[self.__argv.index('-Xc')+1]
            allowedList = []
            allowedRange = []
            if ',' in allowedStatus:
                for status in allowedStatus.split(','):
                    self.__getAllowedStatus(status, allowedList, allowedRange)
            else:
                self.__getAllowedStatus(allowedStatus, allowedList, allowedRange)
            if 200 not in allowedList:
                if oh.askYesNo('warning', "Status code 200 (OK) wasn't included. Do you want to include it to the allowed status codes?"):
                    allowedList = [200] + allowedList
            allowedStatus = {
                'List': allowedList,
                'Range': allowedRange
            }
            matcher.setAllowedStatus(allowedStatus)
            oh.infoBox(f"Set the allowed status codes: {str(allowedStatus)}")
        comparator = {
            'Length': None,
            'Time': None
        }
        if '-Xs' in self.__argv:
            length = self.__argv[self.__argv.index('-Xs')+1]
            comparator['Length'] = int(length)
            oh.infoBox(f"Exclude by length: {length} bytes")
        if '-Xt' in self.__argv:
            time = self.__argv[self.__argv.index('-Xt')+1]
            comparator['Time'] = float(time)
            oh.infoBox(f"Exclude by time: {time} seconds")
        matcher.setComparator(comparator)

    def __getHeader(self, args: list):
        """Get the HTTP header

        @tyoe args: list
        @param args: The list with HTTP header
        @returns dict: The HTTP header parsed into a dict
        """
        httpHeader = {}
        i = 0
        thisArg = args.popleft()
        argsLength = len(args)
        while i < argsLength and thisArg != '':
            key, value = thisArg.split(': ', 1)
            httpHeader[key] = value
            thisArg = args.popleft()
            i += 1
        return httpHeader

    def __getRequestFromRawHttp(self):
        """Get the raw http of the requests

        @returns tuple(str, str, dict, dict): The default parameters of the requests
        """
        headerList = deque(fh.readRaw(self.__argv[self.__argv.index('-r')+1]))
        method, path, httpVer = headerList.popleft().split(' ')
        httpHeader = self.__getHeader(headerList)
        param = {
            'GET': '',
            'POST': ''
        }
        if '?' in path:
            path, param['GET'] = path.split('?', 1)
        # Check if a scheme is specified, otherwise set http as default
        if '--scheme' in self.__argv:
            scheme = self.__argv[self.__argv.index('--scheme')+1]
        else:
            scheme = 'http'
        url = f"{scheme}://{httpHeader['Host']}{path}"
        if method == 'POST' and len(headerList) > 0:
            param['POST'] = headerList.popleft()
        return (url, method, param, httpHeader)
    
    def __getRequestFromArgs(self):
        """Get the param method to use ('?' or '$' in URL if GET, or --data) and the request param string

        @returns tuple(str, str, dict): The tuple with the new target URL, the request method and params
        """
        url = self.getUrl()
        param = {
            'GET': '',
            'POST': ''
        }
        if '?' in url or '$' in url:
            method = 'GET'
            if '?' in url:
                url, param['GET'] = url.split('?', 1)
        else:
            method = 'POST'
            try:
                param['POST'] = self.__argv[self.__argv.index('--data')+1]
            except ValueError:
                oh.errorBox("You must set at least GET or POST parameters for data fuzzing.")
        return (url, method, param)
    
    def __makeParamDict(self, paramDict: dict, param: str):
        """Set the default parameter values if are given

        @type paramDict: dict
        @param paramDict: The entries data of the request
        @type param: str
        @param param: The parameter string of the request
        """
        if '=' in param:
            param, value = param.split('=')
            if not '$' in value:
                paramDict[param] = value
            else:
                paramDict[param] = ''
        else:
            paramDict[param] = ''

    def __getRequestData(self, param: dict):
        """Split all the request parameters into a list of arguments used in the request

        @type param: dict
        @param param: The parameters of the request
        @returns dict: The entries data of the request
        """
        paramDict = {
            'GET': {},
            'POST': {}
        }
        keys = []
        if param['GET']:
            keys.append('GET')
        if param['POST']:
            keys.append('POST')
        if not keys:
            return paramDict
        for key in keys:
            if '&' in param[key]:
                param[key] = param[key].split('&')
                for arg in param[key]:
                    self.__makeParamDict(paramDict[key], arg)
            else:
                self.__makeParamDict(paramDict[key], param[key])
        return paramDict
    
    def __getAllowedStatus(self, status: str, allowedList: list, allowedRange: list):
        """Get the allowed status code list and range

        @type status: str
        @param status: The status cod given in the terminal
        @type allowedList: list
        @param allowedList: The allowed status codes list
        @type allowedRange: list
        @param allowedRange: The range of allowed status codes
        """
        if '-' not in status:
            allowedList.append(int(status))
        else:
            codeLeft, codeRight = (int(code) for code in status.split('-', 1))
            if codeRight < codeLeft:
                codeLeft, codeRight = codeRight, codeLeft
            allowedRange[:] = [codeLeft, codeRight]