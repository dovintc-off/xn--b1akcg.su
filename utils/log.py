from colorama import init, Fore, Style
import inspect
init()
def log(text: str, log_type="info"):
    f = inspect.stack()[1]
    loc = f" ({f.filename.split('/')[-1]}:{f.lineno})" if log_type.lower() != "info" else ""
    colors = {"info": Fore.CYAN, "warning": Fore.YELLOW, "error": Fore.RED}
    color = colors.get(log_type.lower(), Fore.CYAN)
    print(f"{color}[{log_type.upper()}] {text}{Style.RESET_ALL}{Fore.LIGHTBLACK_EX}{loc}{Style.RESET_ALL}")