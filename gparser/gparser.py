from pathlib import Path
import re


class GcodeLine:
    def __init__(
            self,
            command: tuple[str, int],
            params: dict,
            comment: str
    ) -> None:
        self.command = command
        self.params = params
        self.comment = comment

    def decode(
            self,
    ) -> str:
        command_str = ''
        params_str = ''
        comment_str = ''

        if self.command[0] != '#':
            command_str = self.command[0] + str(self.command[1]).zfill(2)

            params_str = ''
            for key, val in self.params.items():
                if key == 'F':
                    params_str += f' {key}{val:.02f}'
                else:
                    params_str += f' {key}{val:.04f}'

            if len(self.comment):
                command_str = ' ' + self.comment

        else:
            comment_str = self.comment

        return command_str + params_str + comment_str


class GcodeParser:
    def __init__(self, gcodeline: list["GcodeLine"]) -> None:
        self.gline = gcodeline

    def __len__(self) -> int:
        return len(self.gline)

    @classmethod
    def from_flatcam(
            cls,
            file_path: Path
    ) -> "GcodeParser":
        with open(file_path, 'r') as f:
            texts = f.read()

        return cls.from_flatcam_bynary(texts)

    @classmethod
    def from_flatcam_bynary(
            cls,
            texts: str
    ) -> "GcodeParser":
        re_not_comennt = r'(?!\( *.+)'  # commnet flag: ()
        re_command = r'(G|M|T)(\d+)'
        re_param = r'(([ \t]*(?!G|M|g|m)[A-Z][-\d\.]*)*)'
        re_comment = r'[ \t]*(\([ \t]*.*)?|(\([ \t]*(.+))'
        re_splitter = re_not_comennt + re_command + re_param + re_comment

        gcodes: list = []
        for text in texts.split("\n"):
            if len(text):
                gcodes += re.findall(re_splitter, text)
            else:
                gcodes += [('', '', '', '', '', '', '')]

        re_param_splitter = r'[ \t]*(?!G|M|g|m)([A-Z])([-\d\.]*)'
        gcodeline: list = []
        for gcode in gcodes:
            param_list = re.findall(re_param_splitter, gcode[2])

            command: tuple[str, int] = ('#', -1)
            params: dict = {}
            comment: str = ''

            if gcode[0]:
                command = (gcode[0], int(gcode[1]))
                params = {param[0]: float(param[1]) for param in param_list}
                comment = gcode[4]

            else:
                comment = gcode[5]

            gcodeline.append(GcodeLine(command, params, comment))

        return cls(gcodeline)

    def save(
            self,
            file_path: Path
    ) -> None:
        gcodes: str = ''
        for gcode in self.gline:
            gcodes += gcode.decode() + '\n'

        with open(file_path, 'w') as f:
            f.write(gcodes)


if __name__ == "__main__":
    gcode = """G0 X46.2033 Y23.673 Z23.6739\n
               G10 X46.2033 Y23.673 Z23.6739\n
               (asdfbth12367G12 X12)\n
               G0 X46.2033 Y23.673 Z23.6739\n
               G0 X46.2033 Y23.673 Z23.6739 (asdfrg)\n
               M30\n"""
    test_path = Path('test.nc')

    gs_bynary = GcodeParser.from_flatcam_bynary(gcode)
    gs_file = GcodeParser.from_flatcam(test_path)

    gs_bynary.save(Path('bynary.nc'))
    gs_file.save(Path('file.nc'))
