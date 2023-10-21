from pathlib import Path
import re


class GcodeLine:
    def __init__(
            self,
            command,
            params,
            comment
    ) -> None:
        self.command = command
        self.params = params
        self.comment = comment

        print(command, params, comment)


class GcodePaser:
    def __init__(self, gcodeline: list["GcodeLine"]) -> None:
        self.gline = gcodeline

    @classmethod
    def from_flatcam(
            cls,
            file_path: Path
    ) -> "GcodePaser":
        with open(file_path, 'r') as f:
            texts = f.read()

        return cls.from_bynary(texts)

    @classmethod
    def from_bynary(
            cls,
            texts: str
    ) -> "GcodePaser":
        re_not_comennt = r'(?!\( *.+)'  # commnet flag: ()
        re_command = r'(G|M|T)(\d+)'
        re_param = r'(([ \t]*(?!G|M|g|m)[A-Z][-\d\.]*)*)'
        re_comment = r'[ \t]*(\([ \t]*.*)?|(\([ \t]*(.+))'
        re_splitter = re_not_comennt + re_command + re_param + re_comment

        gcodes: list = []
        for text in texts.split("\n"):
            gcodes += re.findall(re_splitter, text)

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
                comment = gcode[5]

            else:
                comment = gcode[5]

            gcodeline.append(GcodeLine(command, params, comment))

        return cls(gcodeline)


if __name__ == "__main__":
    gcode = """G0 X46.2033 Y23.673 Z23.6739\n
               G10 X46.2033 Y23.673 Z23.6739\n
               (asdfbth12367G12 X12)\n
               G0 X46.2033 Y23.673 Z23.6739\n
               G0 X46.2033 Y23.673 Z23.6739\n
               M30\n"""

    GcodePaser.from_bynary(gcode)
