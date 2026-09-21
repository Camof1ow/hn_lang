"""
한남랭 (HannamLang) 인터프리터
한글 감탄사/의성어로 구성된 난해한 프로그래밍 언어
엄랭(umjunsik-lang)에서 영감을 받아 제작
"""

import sys


class HannamLang:
    def __init__(self):
        self.memory = {}       # 변수 메모리 (1-indexed)
        self.loops = []        # 루프 시작 위치 스택
        self.pointer = 0       # 명령어 포인터
        self.lines = []        # 명령어 라인들
        self.running = False

    def get_var(self, index):
        """변수값 반환 (미설정시 0)"""
        return self.memory.get(index, 0)

    def set_var(self, index, value):
        """변수값 설정"""
        self.memory[index] = value

    def parse_number(self, expr):
        """
        수식 파싱:
        - `.` = +1, `,` = -1
        - `~` = 물결 카운트 (갯수 = 값)
        - 공백 = 곱셈 연산자
        - `아`×N = N번째 변수값
        - `예?` = stdin 입력

        예시:
        - `티~~~~원` = 4 (물결 4개)
        - `..` = 2
        - `아..` = var[1] + 2
        - `.. ..` = 4 (2×2)
        """
        expr = expr.strip()
        if not expr:
            return 0

        # 곱셈 분리 (공백 기준)
        if ' ' in expr:
            parts = expr.split(' ')
            result = 1
            for part in parts:
                result *= self.parse_number(part)
            return result

        value = 0

        # 변수 참조 (ㅋ 반복)
        kk_count = 0
        temp = expr
        while temp.startswith('ㅋ'):
            kk_count += 1
            temp = temp[1:]
        if kk_count > 0:
            value += self.get_var(kk_count)
            expr = temp

        # 입력 (예?)
        if '예?' in expr:
            try:
                user_input = int(input())
            except (ValueError, EOFError):
                user_input = 0
            expr = expr.replace('예?', '.' * user_input)

        # 물결 카운트 (티~~~~원 → 4)
        tilde_count = expr.count('~')
        if tilde_count > 0:
            value += tilde_count
            expr = expr.replace('~', '')

        # 점/쉼표 카운트
        value += expr.count('.')
        value -= expr.count(',')

        return value

    def parse_line(self, line):
        """
        한 줄 실행.
        반환값:
        - None: 정상 (다음 줄로)
        - int: 점프할 줄 번호 (0-indexed)
        - str: 조건부 실행할 명령어
        """
        line = line.strip()

        # 빈 줄 / 주석
        if not line or line.startswith('#'):
            return None

        # 내아내임 (종료)
        if line.startswith('내아내임'):
            value_expr = line[len('내아내임'):]
            ret = self.parse_number(value_expr)
            print(f"\n[한남랭] 종료. 반환값: {ret}")
            sys.exit(ret)

        # 제가요? (입력) — ㅋ 접두사로 변수 지정
        if '제가요?' in line:
            prefix = line[:line.index('제가요?')]
            kk_count = prefix.count('ㅋ')
            var_index = kk_count + 1
            # 엄 접두사 허용 (하위 호환)
            if prefix.endswith('엄'):
                kk_count = prefix[:-1].count('ㅋ')
                var_index = kk_count + 1
            try:
                val = int(input())
            except (ValueError, EOFError):
                val = 0
            self.set_var(var_index, val)
            return None

        # 요이 (줄 점프)
        if line.startswith('요이'):
            target = self.parse_number(line[len('요이'):])
            return target - 1  # 0-indexed

        # 아뇨아뇨아뇨 (루프 탈출) — 세 번 붙여야 탈출
        if line.startswith('아뇨아뇨아뇨'):
            rest = line[len('아뇨아뇨아뇨'):]
            loop_val = self.parse_number(rest)
            if loop_val != 0:
                return self.pointer + 1
            else:
                if self.loops:
                    return self.loops[-1]
                return None

        # 아뇨 (조건문) — 아뇨{값}?{명령}
        if line.startswith('아뇨') and '?' in line:
            rest = line[len('아뇨'):]
            cond_str, cmd = rest.split('?', 1)
            cond = self.parse_number(cond_str)
            if cond == 0:
                return cmd
            return None

        # ㅋㅋ..엄 (루프 시작)
        if line == 'ㅋㅋ..엄' or line == '예? 저요?':
            self.loops.append(self.pointer)
            return None

        # 티~원 (개행) — 티~~~~원 = 물결 갯수만큼 개행
        if line.startswith('티') and '원' in line and '~' in line:
            inner = line[line.index('티') + 1:line.rindex('원')]
            tilde_count = inner.count('~')
            # 뒤에 값이 있으면 그 값 출력 후 개행
            suffix = line[line.rindex('원') + 1:]
            if suffix:
                val = self.parse_number(suffix)
                print(val, end='')
            for _ in range(max(tilde_count, 1)):
                print()
            return None

        # 줴줴이야 (문자 출력)
        if '줴줴이야' in line:
            value_expr = line[line.index('줴줴이야') + 4:]
            val = self.parse_number(value_expr)
            try:
                print(chr(val), end='')
            except (ValueError, OverflowError):
                print(val, end='')
            return None

        # 엄 (대입) — 엄 뒤에 마침표+반점 합산 최소 3개, 제가요? 입력은 예외
        if '엄' in line:
            var_part, val_part = line.split('엄', 1)
            is_input = '제가요?' in val_part
            punct_count = val_part.count('.') + val_part.count(',')
            if not is_input and (not val_part or punct_count < 3):
                raise SyntaxError(f"엄 뒤에 마침표/반점 3개 이상 필요: {line}")
            kk_count = var_part.count('ㅋ')
            var_index = kk_count if kk_count > 0 else 1
            val = self.parse_number(val_part)
            self.set_var(var_index, val)
            return None

        # 알 수 없는 명령어 (무시)
        return None

    def run(self, code, check=True):
        """
        프로그램 실행.
        code: 소스 코드 문자열
        """
        # 줄바꿈 또는 ~로 분리
        if '~' in code and '\n' not in code:
            self.lines = code.split('~')
        else:
            self.lines = code.split('\n')

        # 시작/종료 검사 (주석 건너뛰기)
        if check:
            code_lines = [l.strip() for l in self.lines if l.strip() and not l.strip().startswith('#')]
            if not code_lines or code_lines[0] != '예? 저요?':
                raise SyntaxError("한남랭은 '예? 저요?'로 시작해야 합니다!")
            if not code_lines[-1].startswith('내아내임'):
                raise SyntaxError("한남랭은 '내아내임'으로 종료해야 합니다!")

        self.running = True
        self.pointer = 0
        max_steps = 100000
        steps = 0

        while self.running and self.pointer < len(self.lines):
            line = self.lines[self.pointer]
            self.pointer += 1

            result = self.parse_line(line)

            if result is not None:
                if isinstance(result, int):
                    # 점프
                    self.pointer = result
                elif isinstance(result, str):
                    # 조건부 명령 실행
                    self.parse_line(result)

            steps += 1
            if steps >= max_steps:
                raise RecursionError("무한 루프가 감지되었습니다!")


def main():
    if len(sys.argv) < 2:
        print("사용법: python hannam.py <파일.한남>")
        print("       python hannam.py -e '<코드>'")
        sys.exit(1)

    if sys.argv[1] == '-e':
        # 코드 직접 실행
        code = sys.argv[2]
    else:
        # 파일 실행
        try:
            with open(sys.argv[1], encoding='utf-8') as f:
                code = f.read()
        except FileNotFoundError:
            print(f"파일을 찾을 수 없습니다: {sys.argv[1]}")
            sys.exit(1)

    interpreter = HannamLang()
    interpreter.run(code)


if __name__ == '__main__':
    main()
