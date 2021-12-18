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

import time
import threading
from typing import Tuple, List, Union

from .cli_arguments import CliArguments
from .cli_output import CliOutput, Colors
from ..argument_builder import ArgumentBuilder as AB
from ... import version
from ...utils.http_utils import get_host, get_pure_url
from ...utils.file_utils import read_file
from ...utils.logger import Logger
from ...core import BlacklistStatus, Dictionary, Fuzzer, Matcher, Payloader
from ...core.defaults.scanners import (DataScanner,
                                       PathScanner, SubdomainScanner)
from ...core.bases import BaseScanner, BaseEncoder
from ...conn.request_parser import check_is_subdomain_fuzzing
from ...conn.requesters import Requester
from ...factories import PluginFactory, RequesterFactory, WordlistFactory
from ...reports.report import Report
from ...objects import Error, Result
from ...exceptions.base_exceptions import FuzzingToolException
from ...exceptions.main_exceptions import (ControllerException, StopActionInterrupt,
                                           WordlistCreationError, BuildWordlistFails)
from ...exceptions.request_exceptions import RequestException


def banner() -> str:
    """Gets the program banner

    @returns str: The program banner
    """
    banner = (f"{Colors.BLUE_GRAY}   ____                        _____       _\n" +
              f"{Colors.BLUE_GRAY}  |  __|_ _ ___ ___ _ ___ ___ |_   _|_ ___| |{Colors.RESET} Version {version()}\n" +
              f"{Colors.BLUE_GRAY}  |  __| | |- _|- _|'|   | . |  | | . | . | |\n" +
              f"{Colors.BLUE_GRAY}  |_|  |___|___|___|_|_|_|_  |  |_|___|___|_|\n" +
              f"{Colors.BLUE_GRAY}                         |___|{Colors.RESET}\n\n" +
              "  [!] Disclaimer: We're not responsible for the misuse of this tool.\n" +
              "      This project was created for educational purposes\n" +
              "      and should not be used in environments without legal authorization.\n")
    return banner


class CliController:
    """Class that handle with the entire application

    Attributes:
        requesters: The requesters list
        started_time: The time when start the fuzzing test
        fuzzer: The fuzzer object to handle with the fuzzing test
        all_results: The results dictionary for each host
        lock: A thread locker to prevent overwrites on logfiles
        blacklist_status: The blacklist status object
        logger: The object to handle with the program log
    """
    def __init__(self):
        self.requester = None
        self.started_time = 0
        self.fuzzer = None
        self.all_results = {}
        self.lock = threading.Lock()
        self.blacklist_status = None
        self.logger = Logger()

    def is_verbose_mode(self) -> bool:
        """The verboseMode getter

        @returns bool: The verbose mode flag
        """
        return self.verbose[0]

    def main(self, arguments: CliArguments) -> None:
        """The main function.
           Prepares the application environment and starts the fuzzing

        @type arguments: CliArguments
        @param arguments: The command line interface arguments object
        """
        self.co = CliOutput()  # Abbreviation to cli output
        self.verbose = arguments.verbose
        if arguments.simple_output:
            self.co.set_simple_output_mode()
        else:
            CliOutput.print(banner())
        try:
            self.co.info_box("Setting up arguments ...")
            self.init(arguments)
            if not arguments.simple_output:
                self.print_configs(arguments)
        except FuzzingToolException as e:
            self.co.error_box(str(e))
        self.co.set_verbosity_mode(self.is_verbose_mode())
        try:
            self.check_connection()
            self.start()
        except KeyboardInterrupt:
            if self.fuzzer and self.fuzzer.is_running():
                self.co.abort_box("Test aborted, stopping threads ...")
                self.fuzzer.stop()
            self.co.abort_box("Test aborted by the user")
        except FuzzingToolException as e:
            self.co.error_box(str(e))
        finally:
            self.show_footer()
            self.co.info_box("Test completed")

    def init(self, arguments: CliArguments) -> None:
        """The initialization function.
           Set the application variables including plugins requires

        @type arguments: CliArguments
        @param arguments: The command line interface arguments object
        """
        self.__init_requesters(arguments)
        scanner = None
        if arguments.scanner:
            scanner, param = arguments.scanner
            scanner: BaseScanner = PluginFactory.object_creator(
                scanner, 'scanners', param
            )
        self.scanner = scanner
        match_status = arguments.match_status
        self.matcher = Matcher(
            match_status,
            arguments.match_length,
            arguments.match_time
        )
        if arguments.blacklisted_status:
            blacklisted_status = arguments.blacklisted_status
            action = arguments.blacklist_action
            self.blacklist_status = BlacklistStatus(
                status=blacklisted_status,
                action=action,
                action_param=arguments.blacklist_action_param,
                action_callbacks={
                    'stop': self._stop_callback,
                    'wait': self._wait_callback,
                },
            )
        self.delay = arguments.delay
        self.number_of_threads = arguments.number_of_threads
        self.__init_report(arguments)
        self.__init_dictionary(arguments)

    def print_configs(self, arguments: CliArguments) -> None:
        """Print the program configuration

        @type arguments: CliArguments
        @param arguments: The command line interface arguments object
        """
        if self.verbose[1]:
            verbose = 'detailed'
        elif self.verbose[0]:
            verbose = 'common'
        else:
            verbose = 'quiet'
        if arguments.lowercase:
            case = 'lowercase'
        elif arguments.uppercase:
            case = 'uppercase'
        elif arguments.capitalize:
            case = 'capitalize'
        else:
            case = None
        self.co.print_configs(
            output='normal'
                   if not arguments.simple_output
                   else 'simple',
            verbose=verbose,
            target=self.target,
            dictionary=self.dict_metadata,
            prefix=arguments.prefix,
            suffix=arguments.suffix,
            case=case,
            encoder=arguments.str_encoder,
            encode_only=arguments.encode_only,
            match={
                'status': arguments.match_status,
                'length': arguments.match_length,
                'time': arguments.match_time,
                },
            scanner=arguments.str_scanner,
            blacklist_status={
                'status': arguments.blacklisted_status,
                'action': arguments.blacklist_action,
                } if arguments.blacklisted_status else {},
            delay=self.delay,
            threads=self.number_of_threads,
            report=arguments.report,
        )

    def check_connection(self) -> None:
        """Test the connection to target.
           If data fuzzing is detected, check for redirections
        """
        self.co.info_box(f"Validating {self.requester.get_url()} ...")
        if self.is_verbose_mode():
            self.co.info_box("Testing connection ...")
        try:
            self.requester.test_connection()
        except RequestException as e:
            if not self.co.ask_yes_no('warning',
                                      f"{str(e)}. Continue anyway?"):
                raise ControllerException("No target left for fuzzing")
        else:
            if self.is_verbose_mode():
                self.co.info_box("Connection status: OK")

    def start(self) -> None:
        """Starts the fuzzing application.
           Each target is fuzzed based on their own methods list
        """
        self.co.info_box("Start fuzzing on "
                            + get_host(get_pure_url(self.requester.get_url())))
        Result.reset_index()
        try:
            self.prepare_target()
            self.started_time = time.time()
            for method in self.requester.methods:
                self.requester.set_method(method)
                self.prepare_fuzzer()
            if not self.is_verbose_mode():
                CliOutput.print("")
        except StopActionInterrupt as e:
            if self.fuzzer and self.fuzzer.is_running():
                self.co.warning_box("Stop action detected, stopping threads ...")
                self.fuzzer.stop()
            self.co.abort_box(f"{str(e)}. Program stopped.")

    def prepare_target(self) -> None:
        """Prepare the target variables for the fuzzing tests.
           Both error logger and default scanners are setted
        """
        self.target_host = get_host(get_pure_url(self.requester.get_url()))
        if self.is_verbose_mode():
            self.co.info_box(f"Preparing target {self.target_host} ...")
        self.check_ignore_errors(self.target_host)
        self.results = []
        self.stop_action = None
        self.__prepare_matcher()
        self.__prepare_scanner()
        self.total_requests = (len(self.dictionary)
                               * len(self.requester.methods))

    def prepare_fuzzer(self) -> None:
        """Prepare the fuzzer for the fuzzing tests.
           Refill the dictionary with the wordlist
           content if a global dictionary was given
        """
        self.dictionary.reload()
        self.fuzzer = Fuzzer(
            requester=self.requester,
            dictionary=self.dictionary,
            matcher=self.matcher,
            scanner=self.scanner,
            delay=self.delay,
            number_of_threads=self.number_of_threads,
            blacklist_status=self.blacklist_status,
            result_callback=self._result_callback,
            exception_callbacks=[
                self._invalid_hostname_callback,
                self._request_exception_callback
            ],
        )
        self.fuzzer.start()
        while self.fuzzer.join():
            if self.stop_action:
                raise StopActionInterrupt(self.stop_action)

    def check_ignore_errors(self, host: str) -> None:
        """Check if the user wants to ignore the errors during the tests.
           By default, URL fuzzing (path and subdomain) ignore errors

        @type host: str
        @param host: The target hostname
        """
        if (self.requester.is_url_discovery() or
                self.co.ask_yes_no('info',
                                   ("Do you want to ignore errors on this "
                                    "target, and save them into a log file?"))):
            self.ignore_errors = True
            log_path = self.logger.setup(host)
            self.co.info_box(f'The logs will be saved on \'{log_path}\'')
        else:
            self.ignore_errors = False

    def show_footer(self) -> None:
        """Show the footer content of the software, after maked the fuzzing.
           The results are shown for each target
        """
        if self.fuzzer:
            if self.started_time:
                self.co.info_box(
                    f"Time taken: {float('%.2f'%(time.time() - self.started_time))} seconds"
                )
            if self.results:
                self.__handle_valid_results(self.target_host, self.results)
            else:
                self.co.info_box(
                    f"No matched results was found for {self.target_host}"
                )

    def _stop_callback(self, status: int) -> None:
        """The skip target callback for the blacklist_action

        @type status: int
        @param status: The identified status code into the blacklist
        """
        self.stop_action = f"Status code {str(status)} detected"

    def _wait_callback(self, status: int) -> None:
        """The wait (pause) callback for the blacklist_action

        @type status: int
        @param status: The identified status code into the blacklist
        """
        if not self.fuzzer.is_paused():
            self.fuzzer.pause()
            self.co.warning_box(
                f"Status code {str(status)} detected. Pausing threads ..."
            )
            self.fuzzer.wait_until_pause()
            if not self.is_verbose_mode():
                CliOutput.print("")
            self.co.info_box(
                f"Waiting for {self.blacklist_status.action_param} seconds ..."
            )
            time.sleep(self.blacklist_status.action_param)
            self.co.info_box("Resuming target ...")
            self.fuzzer.resume()

    def _result_callback(self, result: Result, validate: bool) -> None:
        """Callback function for the results output

        @type result: Result
        @param result: The FuzzingTool result
        @type validate: bool
        @param validate: A validator flag for the result, gived by the scanner
        """
        if self.verbose[0]:
            if validate:
                self.results.append(result)
            self.co.print_result(result, validate)
        else:
            if validate:
                self.results.append(result)
                self.co.print_result(result, validate)
            self.co.progress_status(
                result.index, self.total_requests, result.payload
            )

    def _request_exception_callback(self, error: Error) -> None:
        """Callback that handle with the request exceptions

        @type error: Error
        @param error: The error gived by the exception
        """
        if self.ignore_errors:
            if not self.verbose[0]:
                self.co.progress_status(
                    error.index, self.total_requests, error.payload
                )
            else:
                if self.verbose[1]:
                    self.co.not_worked_box(str(error))
            with self.lock:
                self.logger.write(str(error), error.payload)
        else:
            self.stop_action = str(error)

    def _invalid_hostname_callback(self, error: Error) -> None:
        """Callback that handle with the subdomain hostname resolver exceptions

        @type error: Error
        @param error: The error gived by the exception
        """
        if self.verbose[0]:
            if self.verbose[1]:
                self.co.not_worked_box(str(error))
        else:
            self.co.progress_status(
                error.index, self.total_requests, error.payload
            )

    def __get_target_fuzzing_type(self, requester: Requester) -> str:
        """Get the target fuzzing type, as a string format

        @type requester: Requester
        @param requester: The actual iterated requester
        @return str: The fuzzing type, as a string
        """
        if requester.is_method_fuzzing():
            return "MethodFuzzing"
        elif requester.is_data_fuzzing():
            return "DataFuzzing"
        elif requester.is_url_discovery():
            if requester.is_path_fuzzing():
                return "PathFuzzing"
            else:
                return "SubdomainFuzzing"
        else:
            return "Couldn't determine the fuzzing type"

    def __init_requesters(self, arguments: CliArguments) -> None:
        """Initialize the requester

        @type arguments: CliArguments
        @param arguments: The command line interface arguments object
        """
        self.target = None
        if arguments.target_from_url:
            self.target = AB.build_target_from_args(
                arguments.target_from_url, arguments.method, arguments.data
            )
        if arguments.target_from_raw_http:
            self.target = AB.build_target_from_raw_http(
                arguments.target_from_raw_http, arguments.scheme
            )
        if not self.target:
            raise ControllerException("A target is needed to make the fuzzing")
        if check_is_subdomain_fuzzing(self.target['url']):
            requester_type = 'SubdomainRequester'
        else:
            requester_type = 'Requester'
        self.requester = RequesterFactory.creator(
            requester_type,
            url=self.target['url'],
            methods=self.target['methods'],
            body=self.target['body'],
            headers=self.target['header'],
            follow_redirects=arguments.follow_redirects,
            proxy=arguments.proxy,
            proxies=(read_file(arguments.proxies)
                        if arguments.proxies else []),
            timeout=arguments.timeout,
            cookie=arguments.cookie,
        )
        self.target['type_fuzzing'] = self.__get_target_fuzzing_type(self.requester)

    def __init_report(self, arguments: CliArguments) -> None:
        """Initialize the report

        @type arguments: CliArguments
        @param arguments: The command line interface arguments object
        """
        self.report = Report.build(arguments.report)
        Result.save_payload_configs = arguments.save_payload_conf
        Result.save_headers = arguments.save_headers
        Result.save_body = arguments.save_body

    def __build_encoders(self, arguments: CliArguments) -> Union[
        Tuple[List[BaseEncoder], List[List[BaseEncoder]]], None
    ]:
        """Build the encoders

        @type arguments: CliArguments
        @param arguments: The command line interface arguments object
        @returns Tuple | None: The encoders used in the program
        """
        if not arguments.encoder:
            return None
        if arguments.encode_only:
            Payloader.encoder.set_regex(arguments.encode_only)
        encoders_default = []
        encoders_chain = []
        for encoders in arguments.encoder:
            if len(encoders) > 1:
                append_to = []
                is_chain = True
            else:
                append_to = encoders_default
                is_chain = False
            for encoder in encoders:
                name, param = encoder
                encoder = PluginFactory.object_creator(
                    name, 'encoders', param
                )
                append_to.append(encoder)
            if is_chain:
                encoders_chain.append(append_to)
        return (encoders_default, encoders_chain)

    def __configure_payloader(self, arguments: CliArguments) -> None:
        """Configure the Payloader options

        @type arguments: CliArguments
        @param arguments: The command line interface arguments object
        """
        Payloader.set_prefix(arguments.prefix)
        Payloader.set_suffix(arguments.suffix)
        if arguments.lowercase:
            Payloader.set_lowercase()
        elif arguments.uppercase:
            Payloader.set_uppercase()
        elif arguments.capitalize:
            Payloader.set_capitalize()
        encoders = self.__build_encoders(arguments)
        if encoders:
            Payloader.encoder.set_encoders(encoders)

    def __build_wordlist(
        self,
        wordlists: List[Tuple[str, str]],
        requester: Requester = None
    ) -> list:
        """Build the wordlist

        @type wordlists: List[Tuple[str, str]]
        @param wordlists: The wordlists used in the dictionary
        @type requester: Requester
        @param requester: The requester for the given dictionary
        @returns List: The builded wordlist list
        """
        builded_wordlist = []
        for wordlist in wordlists:
            name, params = wordlist
            if self.verbose[1]:
                self.co.info_box(f"Building wordlist from {name} ...")
            self.dict_metadata['wordlists'].append(
                f"{name}={params}" if params else name
            )
            try:
                wordlist_obj = WordlistFactory.creator(name, params, requester)
                wordlist_obj.build()
            except (WordlistCreationError, BuildWordlistFails) as e:
                if self.is_verbose_mode():
                    self.co.warning_box(str(e))
            else:
                builded_wordlist.extend(wordlist_obj.get())
                if self.verbose[1]:
                    self.co.info_box(f"Wordlist {name} builded")
        if not builded_wordlist:
            raise ControllerException("The wordlist is empty")
        return builded_wordlist

    def __build_dictionary(
        self,
        wordlists: List[Tuple[str, str]],
        is_unique: bool,
        requester: Requester = None
    ) -> Dictionary:
        """Build the dictionary

        @type wordlists: List[Tuple[str, str]]
        @param wordlists: The wordlists used in the dictionary
        @type is_unique: bool
        @param is_unique: A flag to say if the dictionary will contains only unique payloads
        @type requester: Requester
        @param requester: The requester for the given dictionary
        @returns Dictionary: The dictionary object
        """
        self.dict_metadata = {
            'wordlists': [],
            'len': 0
        }
        builded_wordlist = self.__build_wordlist(wordlists, requester)
        atual_length = len(builded_wordlist)
        if is_unique:
            previous_length = atual_length
            builded_wordlist = set(builded_wordlist)
            atual_length = len(builded_wordlist)
            self.dict_metadata['removed'] = previous_length-atual_length
        dictionary = Dictionary(builded_wordlist)
        self.dict_metadata['len'] = atual_length
        return dictionary

    def __init_dictionary(self, arguments: CliArguments) -> None:
        """Initialize the dictionary

        @type arguments: CliArguments
        @param arguments: The command line interface arguments object
        """
        self.__configure_payloader(arguments)
        self.dictionary = []
        self.dict_metadata = []
        self.dictionary = self.__build_dictionary(
            arguments.wordlist, arguments.unique, self.requester
        )

    def __prepare_matcher(self) -> None:
        """Prepares the local matcher"""
        if (self.requester.is_url_discovery() and
                self.matcher.allowed_status_is_default()):
            self.matcher.set_allowed_status("200-399,401,403")

    def __get_default_scanner(self) -> BaseScanner:
        """Check what's the scanners that will be used

        @returns BaseScanner: The scanner used in the fuzzing tests
        """
        if self.requester.is_url_discovery():
            if self.requester.is_path_fuzzing():
                scanner = PathScanner()
            else:
                scanner = SubdomainScanner()
        else:
            scanner = DataScanner()
        self.co.set_message_callback(scanner.cli_callback)
        return scanner

    def __get_data_comparator(self) -> tuple:
        """Check if the user wants to insert
           custom data comparator to validate the responses

        @returns tuple: The data comparator tuple for the Matcher object
        """
        payload = ' '  # Set an arbitraty payload
        self.co.info_box(
            f"Making first request with '{payload}' as payload ..."
        )
        try:
            # Make the first request to get some info about the target
            response, rtt = self.requester.request(payload)
        except RequestException as e:
            raise StopActionInterrupt(str(e))
        result_to_comparator = Result(response, rtt)
        self.co.print_result(result_to_comparator, False)
        length = None
        default_length = int(result_to_comparator.body_length)+300
        if self.co.ask_yes_no('info',
                              ("Do you want to exclude responses "
                               "based on custom length?")):
            length = self.co.ask_data(
                f"Insert the length (in bytes, default >{default_length})"
            )
            if not length:
                length = default_length
        time = None
        default_time = result_to_comparator.rtt+5.0
        if self.co.ask_yes_no('info',
                              ("Do you want to exclude responses "
                               "based on custom time?")):
            time = self.co.ask_data(
                f"Insert the time (in seconds, default >{default_time} seconds)"
            )
            if not time:
                time = default_time
        return (length, time)

    def __prepare_scanner(self) -> None:
        """Prepares the scanner"""
        if not self.scanner:
            self.scanner = self.__get_default_scanner()
            if (self.requester.is_data_fuzzing() and
                    not self.matcher.comparator_is_set()):
                self.co.info_box("DataFuzzing detected, checking for a data comparator ...")
                self.matcher.set_comparator(*self.__get_data_comparator())
        self.co.set_message_callback(self.scanner.cli_callback)

    def __handle_valid_results(self,
                               host: str,
                               results: list) -> None:
        """Handle the valid results from footer

        @type host: str
        @param host: The target host
        @type results: list
        @param results: The target results from the fuzzing
        """
        if self.is_verbose_mode():
            self.co.info_box(
                f"Found {len(results)} matched results on target {host}"
            )
            for result in results:
                self.co.print_result(result, True)
            self.co.info_box(f'Saving results for {host} ...')
        report_path = self.report.open(host)
        self.report.write(results)
        self.co.info_box(f"Results saved on {report_path}")
