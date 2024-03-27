from my_docopt import docopt, DocoptExit
from disk_with_handle import DiskWithHandle
from rich import print as rprint

DOC = """
UNIX V6++ 文件系统模拟器

用法：
    $ ls
    $ cd <dirname>
    $ mkdir <dir>
    $ fcreat <filename>
    $ fopen <filename>
    $ fclose <handle>
    $ fread <handle> <size>
    $ fwrite <handle> <content>
    $ flseek <handle>
    $ fdelete <filename>
    $ fformat
    $ help
    $ unmount
    
参数：
    -d, --debug         输出debug信息
"""

class Terminal:
    def __init__(self, image: str):
        self.disk = DiskWithHandle(image)
        self.disk.mount()
        self.path = "/"
        print(DOC)

    def process(self, args: dict) -> bool:
        if args['ls']:
            pass

        if args['cd']:
            pass

        if args['mkdir']:
            pass

        if args['fcreat']:
            pass

        if args['fopen']:
            pass

        if args['fclose']:
            pass

        if args['fread']:
            pass

        if args['fwrite']:
            pass

        if args['flseek']:
            pass

        if args['fdelete']:
            pass

        if args['fformat']:
            pass

        if args['help']:
            pass

        if args['unmount']:
            self.disk.unmount()
            return False
        return True

    def loop(self):
        rprint(f"[bold green]UNIX V6++ FS[/bold green] [bold blue]{self.path} [/bold blue]$ ", end='')
        command = input()
        args = command.split()
        try:
            args = docopt(DOC, args, help=False)
        except DocoptExit:
            return True
        return self.process(args)

t = Terminal("disk.img")
while t.loop():
    pass