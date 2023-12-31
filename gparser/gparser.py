from typing import Iterable, Optional
from pathlib import Path
import re
import copy
import warnings


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

    def __repr__(self) -> str:
        return self.encode()

    def encode(
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
                comment_str = ' ' + self.comment

        else:
            comment_str = self.comment

        return command_str + params_str + comment_str


class GcodeParser:
    def __init__(self, gcodelines: list["GcodeLine"]) -> None:
        self.glines = gcodelines

    def __iter__(self) -> Iterable["GcodeLine"]:
        yield from self.glines

    def __len__(self) -> int:
        return len(self.glines)

    def __repr__(self) -> str:
        return "{}".format("\n".join(repr(x) for x in self.glines))

    def _check_uniquely_decodable(
            self,
            texts: str
    ) -> None:
        """一意復号可能のチェック

        構文解析したデータを再度ncファイルに戻りしたとき，元のncファイルと一致するかどうか確認

        Args:
            texts: 元のncファイルのテキスト
        """
        i = 1
        for gline, text in zip(self.glines, texts.split("\n")):
            if gline.encode() != text.strip():
                correct = False

                # Exception for FlatCAM  (M05 == M5)
                if gline.command[0] in ['M', 'T']:
                    correct = gline.command[1] == int(text.strip()[1:])

                # Exception for FlatCAM  (G00 Z15.0000 == G00 Z15.00)
                if gline.command == ('G', 0):
                    correct = gline.params == {'Z': 5.0}

                # assert
                assert correct, f'Load error [{i} line]: (load, correct) -> ({gline}, {text})'
                warnings.warn(f'[{i} line] {gline} {text.strip()}')
            i += 1

    @classmethod
    def from_flatcam(
            cls,
            file_path: Path
    ) -> "GcodeParser":
        """ncファイルから構文解析

        各行をコマンド，パラメータ，コメントで分ける

        Args:
            file_path: ncファイルのファイルパス

        Returns:
            自身のクラスオブジェクト（構文解析したGcodeを持つ）
        """
        print(f'load file: {file_path}')
        with open(file_path, 'r') as f:
            texts = f.read()

        return cls.from_flatcam_bynary(texts)

    @classmethod
    def from_flatcam_bynary(
            cls,
            texts: str
    ) -> "GcodeParser":
        """テキストデータから構文解析

        各行をコマンド，パラメータ，コメントで分ける

        Args:
            texts: 改行を含むGcodeのtextデータ

        Returns:
            自身のクラスオブジェクト（構文解析したGcodeを持つ）
        """
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

            command: tuple[str, int] = ('#', -1)  # default: comment
            params: dict = {}
            comment: str = ''

            if gcode[0]:
                command = (gcode[0], int(gcode[1]))
                params = {param[0]: float(param[1]) for param in param_list}
                comment = gcode[4]

            else:
                comment = gcode[5]

            gcodeline.append(GcodeLine(command, params, comment))

        # Check for correct parsing
        gparser = cls(gcodeline)
        gparser._check_uniquely_decodable(texts)

        return gparser

    def save(
            self,
            file_path: Path
    ) -> None:
        """ncファイルとして保存

        Args:
            file_path: 保存するファイルパス
        """
        gcodes: str = ''
        for gcode in self.glines:
            gcodes += gcode.encode() + '\n'

        with open(file_path, 'w') as f:
            f.write(gcodes)

    def find_command(
            self,
            command: tuple[str, int],
            params: Optional[dict] = None,
            start_i: int = 0,
            end_i: Optional[int] = None,
            first_only: bool = False
    ) -> list[int]:
        """指定したコマンドとマッチする index を検索する

        Args:
            command   : コマンド             ex) ('G', 0), ('M', 5), etc
            params    : コマンドのパラメータ  ex) {'X': 10, 'Y': 0}, etc
            start_i   : 検索を開始する index
            end_i     : 検索を終了する index
            first_only: ヒットする箇所が複数ある時，最初のヒットで検索を終了するかどうか

        Returns:
            マッチした Gcode の index  (絶対位置)
        """
        index = []
        for i, gcode in enumerate(self.glines[start_i:end_i]):
            if gcode.command != command:
                continue

            if (params is not None) and (gcode.params != params):
                continue

            index.append(start_i + i)

            if first_only:
                break

        return index

    def match_lines(
            self,
            glines: "GcodeParser",
            start_i: int = 0,
            end_i: Optional[int] = None,
            first_only: bool = False
    ) -> list[int]:
        """指定したコードとマッチする箇所の検索

        指定した Gcode(複数行可能) とマッチする箇所の index を取得する
        index は最初の行番号 (0 ~ n)
        ※ コメント文も検索されるが，内容のマッチングはしない（あくまでもコメント文があるという判定のみ）

        Args:
            glines    : 検索コード (このコードとマッチする行を検索する)
            start_i   : 検索を開始する index
            end_i     : 検索を終了する index
            first_only: ヒットする箇所が複数ある時，最初のヒットで検索を終了するかどうか

        Returns:
            マッチした Gcode の最初の index  (絶対位置)
            first_only が True の時，最初にマッチした箇所のみを返す

        Example:
            対象コード
            >>> G00 X46.2033 Y23.6730 Z23.6739
                G10 X46.2033 Y23.6730 Z23.6739
                (asdfbth12367G12 X12)
                G10 X46.2033 Y23.6730 Z23.6739
                (asdfbth12367G12 X12)
                M30

            検索コード
            >>> G10 X46.2033 Y23.6730 Z23.6739
                (asdfbth12367G12 X12)

            返り値
            >>> [1, 3]
        """
        _glines = copy.deepcopy(glines)
        gline = _glines.glines.pop(0)
        indices = self.find_command(gline.command, gline.params, start_i, end_i, first_only)

        if _glines:
            next_i = [i + 1 for i in indices]
            for i, start_i in enumerate(next_i):
                _glines_cp = copy.deepcopy(_glines)
                if len(self.match_lines(_glines_cp, start_i, start_i + 1, first_only)) == 0:
                    indices[i] = -1

                if first_only:
                    break

        return [index for index in indices if index != -1]


if __name__ == "__main__":
    gcode = """G00 X46.2033 Y23.6730 Z23.6739
               G10 X46.2033 Y23.6730 Z23.6739
               (asdfbth12367G12 X12)
               G00 X46.2033 Y23.6730 Z23.0000

               G00 X46.2033 Y23.6730 Z23.6739 (asdfrg)
               G10 X46.2033 Y23.6730 Z23.6739
               M30"""
    gcode_match = """G00 X46.2033 Y23.6730 Z23.6739
                     G10 X46.2033 Y23.6730 Z23.6739"""
    test_path = Path('a.nc')

    # Load Gcode
    gs_binary = GcodeParser.from_flatcam_bynary(gcode)
    gs_binary_match = GcodeParser.from_flatcam_bynary(gcode_match)
    gs_file = GcodeParser.from_flatcam(test_path)

    # Search Gcode
    print(gs_binary.match_lines(gs_binary_match, first_only=True))
    print(gs_file.find_command(('M', 5)))

    # Save Gcode
    gs_binary.save(Path('bynary.nc'))
    gs_file.save(Path('file.nc'))
