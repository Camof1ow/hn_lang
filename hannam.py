"""
한남랭 (HannamLang) 인터프리터 v3.0
한글 감탄사/의성어로 구성된 난해한 프로그래밍 언어
엄랭(umjunsik-lang)에서 영감을 받아 제작

사용법:
    python hannam.py <파일.한남>
    python hannam.py --debug <파일.한남>
    python hannam.py --ast <파일.한남>
    python hannam.py --repl
"""

import sys
import re

# ══════════════════════════════════════════════════════════════
# 키워드 상수
# ══════════════════════════════════════════════════════════════

K_K = '\u314B'                    # ㅋ (변수 접두사)
K_ASSIGN = '\uC5C4'               # 엄 (대입)
K_PRINT = '\uC934\uC934\uC774\uC57C'  # 줴줴이야 (출력)
K_INPUT = '\uC81C\uAC00\uC694?'   # 제가요? (입력)
K_NEWLINE_KW = '\uD2F0'           # 티 (개행 시작)
K_NEWLINE_END = '\uC6D0'          # 원 (개행 끝)
K_LOOP_START = f'{K_K}{K_K}..{K_K}{K_K}'  # ㅋㅋ..ㅋㅋ (루프 시작)
K_LOOP_BREAK = '\uC544\uB1E8\uC544\uB1E8\uC544\uB1E8'  # 아뇨아뇨아뇨
K_COND = '\uC544\uB1E8'           # 아뇨 (조건문)
K_JUMP = '\uC694\uC774'           # 요이 (줄 점프)
K_EXIT = '\uB0B4\uC544\uB0B4\uC784'  # 내아내임 (종료)
K_START = '\uC608? \uC800\uC694?' # 예? 저요? (시작)
K_FUNC_DEF = '\uC934\uB77C'       # 쥐랄 (함수 선언)
K_FUNC_END = '\uC934\uB77C\uCE5C\uCE5C'  # 쥐랄ㅋㅋ (함수 끝)
K_CALL = '\uC5B4\uC774'           # 어이 (함수 호출)
K_EQ = '\uC934~\uB77C'            # 쥐~랄 (==)
K_GT = '\uC934~~\uB77C'           # 쥐~~랄 (>)
K_LT = '\uC934~~~\uB77C'          # 쥐~~~랄 (<)
K_NE = '\uC934\uD788\uB77C'      # 쥐히랄 (!=)

# ── 테이프 (Brainfuck 스타일) ──
K_TAPE_RIGHT = '\uB4DC\uAC00\uC7AC'          # 드가재 (>)
K_TAPE_LEFT = '\uB108\uB098\uAC00\uB77C'     # 넌나가라 (<)
K_TAPE_INC = '\uC5B4\uD788'                   # 어흐 (+)
K_TAPE_DEC = '\uC544\uD788'                   # 아흐 (-)
K_TAPE_OUT = '\uC608\uC5D0?'                  # 예에? (.)
K_TAPE_IN = '\uC608?'                         # 예? (,)
K_TAPE_LOOP_START = '\uC316'                  # 엌 ([)
K_TAPE_LOOP_END = '\uC316\uCE5C'             # 엌ㅋ (])


# ══════════════════════════════════════════════════════════════
# 수식 파서 (연산자 우선순위: 비교 < 덧셈 < 곱셈 < 단항)
# ══════════════════════════════════════════════════════════════

class ExprParser:
    """수식 파서: 사칙연산, 괄호, 변수 참조, 비교 연산 지원"""

    def __init__(self, get_var_fn):
        self.get_var = get_var_fn
        self.s = ''
        self.pos = 0

    def parse(self, expr):
        expr = expr.strip()
        if not expr:
            return 0
        # 공백 = 곱셈 연산자 (전처리)
        # 점/쉼표/ㅋ/닫는괄호 뒤 + 숫자/ㅋ/여는괄호 앞 → 곱셈
        expr = re.sub(r'(?<=[.,\)\u314B])\s+(?=[.,\(\u314B\d])', '*', expr)
        expr = re.sub(r'\s+', '', expr)
        self.s = expr
        self.pos = 0
        result = self._expr()
        return result

    def _peek(self):
        return self.s[self.pos] if self.pos < len(self.s) else None

    def _advance(self):
        self.pos += 1

    def _expr(self):
        return self._comparison()

    def _comparison(self):
        left = self._additive()
        while self._peek() == '\uC934':  # 쥐
            saved = self.pos
            if self.s[self.pos:].startswith(K_NE):
                self.pos += len(K_NE)
                right = self._additive()
                left = 1 if left != right else 0
            elif self.s[self.pos:].startswith(K_LT):
                self.pos += len(K_LT)
                right = self._additive()
                left = 1 if left < right else 0
            elif self.s[self.pos:].startswith(K_GT):
                self.pos += len(K_GT)
                right = self._additive()
                left = 1 if left > right else 0
            elif self.s[self.pos:].startswith(K_EQ):
                self.pos += len(K_EQ)
                right = self._additive()
                left = 1 if left == right else 0
            else:
                break
        return left

    def _additive(self):
        left = self._multiplicative()
        while self._peek() in ('+', '-'):
            op = self._peek()
            self._advance()
            right = self._multiplicative()
            left = left + right if op == '+' else left - right
        return left

    def _multiplicative(self):
        left = self._unary()
        while self._peek() in ('*', '/', '%'):
            op = self._peek()
            self._advance()
            right = self._unary()
            if op == '*':
                left *= right
            elif op == '/':
                left = int(left / right) if right != 0 else 0
            else:
                left = left % right if right != 0 else 0
        return left

    def _unary(self):
        if self._peek() == '-':
            self._advance()
            return -self._atom()
        if self._peek() == '+':
            self._advance()
            return self._atom()
        return self._atom()

    def _atom(self):
        c = self._peek()
        if c is None:
            return 0

        # 숫자 리터럴
        if c.isdigit():
            start = self.pos
            while self.pos < len(self.s) and self.s[self.pos].isdigit():
                self.pos += 1
            return int(self.s[start:self.pos])

        # 괄호
        if c == '(':
            self._advance()
            val = self._expr()
            if self._peek() == ')':
                self._advance()
            return val

        # stdin 입력
        if c == '\uC608' and self.pos + 1 < len(self.s) and self.s[self.pos + 1] == '?':
            self._advance()
            self._advance()
            try:
                return int(input("입력: "))
            except (ValueError, EOFError):
                return 0

        # 변수 참조 (ㅋ×N)
        if c == K_K:
            count = 0
            while self.pos < len(self.s) and self.s[self.pos] == K_K:
                count += 1
                self.pos += 1
            val = self.get_var(count)
            # 뒤따르는 ./,/~ 도 같은 원자에 포함
            while self.pos < len(self.s) and self.s[self.pos] in ('.', ',', '~'):
                ch = self.s[self.pos]
                if ch == '.':
                    val += 1
                elif ch == ',':
                    val -= 1
                elif ch == '~':
                    val += 1
                self.pos += 1
            return val

        # 숫자 표현 (. = +1, , = −1, ~ = 카운트)
        if c in ('.', ',', '~'):
            val = 0
            while self.pos < len(self.s) and self.s[self.pos] in ('.', ',', '~'):
                ch = self.s[self.pos]
                if ch == '.':
                    val += 1
                elif ch == ',':
                    val -= 1
                elif ch == '~':
                    val += 1
                self.pos += 1
            return val

        raise SyntaxError(f"알 수 없는 토큰: '{c}' (위치 {self.pos})")


# ══════════════════════════════════════════════════════════════
# 명령어 (AST 노드)
# ══════════════════════════════════════════════════════════════

class Inst:
    __slots__ = ('kind', 'data')

    def __init__(self, kind, **data):
        self.kind = kind
        self.data = data

    def __repr__(self):
        d = {k: v for k, v in self.data.items() if k != 'line'}
        return f"Inst({self.kind}, {d})"


# ══════════════════════════════════════════════════════════════
# 인터프리터
# ══════════════════════════════════════════════════════════════

class HannamLang:
    def __init__(self, debug=False):
        self.debug = debug
        self.memory = {}
        self.functions = {}
        self.instructions = []
        self.loop_stack = []
        self.pc = 0
        self.parser = ExprParser(lambda idx: self.memory.get(idx, 0))
        # 테이프 (Brainfuck 스타일)
        self.tape = [0] * 30000
        self.tape_ptr = 0

    def _val(self, expr, ctx=""):
        return self.parser.parse(expr)

    # ── 파싱 ──

    def parse(self, source):
        lines = source.split('\n')
        self.instructions = []
        self.functions = {}
        i = 0
        while i < len(lines):
            line = self._clean(lines[i])
            lineno = i + 1

            if not line:
                self.instructions.append(Inst('nop', line=lineno))
                i += 1
                continue

            # 함수 선언
            if line.startswith(K_FUNC_DEF) and len(line) > len(K_FUNC_DEF):
                name = line[len(K_FUNC_DEF):].strip()
                body_lines = []
                i += 1
                while i < len(lines):
                    bl = self._clean(lines[i])
                    if bl == K_FUNC_END:
                        break
                    body_lines.append(lines[i])
                    i += 1
                else:
                    raise SyntaxError(f"함수 '{name}'에 '{K_FUNC_END}'가 없습니다 (줄 {lineno})")
                self.functions[name] = self._parse_body(body_lines, lineno)
                self.instructions.append(Inst('nop', line=lineno))
                i += 1
                continue

            inst = self._parse_line(line, lineno)
            self.instructions.append(inst)
            i += 1

            # 테이프 루프 시작 (ㅋ) → 본체 수집
            if inst.kind == 'tape_loop_start':
                body = []
                depth = 1
                while i < len(lines):
                    bl = self._clean(lines[i])
                    if bl == K_TAPE_LOOP_START:
                        depth += 1
                    elif bl == K_TAPE_LOOP_END:
                        depth -= 1
                        if depth == 0:
                            self.instructions[-1] = Inst('tape_loop', line=lineno, body=body)
                            i += 1
                            break
                    body.append(self._parse_line(bl, i))
                    i += 1

        # 시작/종료 검증
        real = [i for i in self.instructions if i.kind != 'nop']
        if not real or real[0].kind != 'start':
            raise SyntaxError("한남랭은 '예? 저요?'로 시작해야 합니다!")
        if real[-1].kind != 'exit':
            raise SyntaxError("한남랭은 '내아내임'으로 종료해야 합니다!")

    def _clean(self, line):
        line = line.strip()
        if '#' in line:
            line = line[:line.index('#')].strip()
        return line

    def _parse_body(self, raw_lines, base_lineno):
        """함수 본체를 Instruction 리스트로 파싱 (루프 지원)"""
        insts = []
        i = 0
        while i < len(raw_lines):
            line = self._clean(raw_lines[i])
            lineno = base_lineno + i

            if not line:
                i += 1
                continue

            # 루프 시작 (ㅋㅋ..ㅋㅋ)
            if line == K_LOOP_START:
                body = []
                i += 1
                while i < len(raw_lines):
                    bl = self._clean(raw_lines[i])
                    if bl.startswith(K_LOOP_BREAK):
                        cond = bl[len(K_LOOP_BREAK):].strip()
                        insts.append(Inst('loop', line=lineno,
                                          body=body, condition=cond))
                        i += 1
                        break
                    body.append(self._parse_line(bl, base_lineno + i))
                    i += 1
                continue

            # 테이프 루프 시작 (ㅋ)
            if line == K_TAPE_LOOP_START:
                body = []
                i += 1
                depth = 1
                while i < len(raw_lines):
                    bl = self._clean(raw_lines[i])
                    if bl == K_TAPE_LOOP_START:
                        depth += 1
                    elif bl == K_TAPE_LOOP_END:
                        depth -= 1
                        if depth == 0:
                            insts.append(Inst('tape_loop', line=lineno, body=body))
                            i += 1
                            break
                    body.append(self._parse_line(bl, base_lineno + i))
                    i += 1
                continue

            insts.append(self._parse_line(line, lineno))
            i += 1
        return insts

    def _parse_line(self, line, lineno):
        """단일 줄을 Instruction으로 파싱"""

        # 시작
        if line == K_START:
            return Inst('start', line=lineno)

        # 종료
        if line.startswith(K_EXIT):
            return Inst('exit', line=lineno, value=line[len(K_EXIT):].strip())

        # 입력
        if K_INPUT in line:
            prefix = line[:line.index(K_INPUT)]
            return Inst('input', line=lineno, var=prefix.count(K_K) + 1)

        # 줄 점프
        if line.startswith(K_JUMP):
            return Inst('jump', line=lineno, target=line[len(K_JUMP):].strip())

        # 루프 탈출
        if line.startswith(K_LOOP_BREAK):
            return Inst('loop_break', line=lineno,
                        condition=line[len(K_LOOP_BREAK):].strip())

        # 조건문
        if line.startswith(K_COND) and '?' in line[len(K_COND):]:
            rest = line[len(K_COND):]
            q = rest.index('?')
            return Inst('cond', line=lineno,
                        condition=rest[:q].strip(),
                        command=rest[q+1:].strip())

        # 루프 시작
        if line == K_LOOP_START:
            return Inst('loop_start', line=lineno)

        # 개행
        if line.startswith(K_NEWLINE_KW) and K_NEWLINE_END in line and '~' in line:
            inner = line[line.index(K_NEWLINE_KW)+1:line.rindex(K_NEWLINE_END)]
            suffix = line[line.rindex(K_NEWLINE_END)+1:]
            return Inst('newline', line=lineno,
                        count=max(inner.count('~'), 1),
                        suffix=suffix.strip())

        # 출력 (kk이야)
        if K_PRINT in line:
            pos = line.index(K_PRINT)
            prefix = line[:pos]
            rest = line[pos+len(K_PRINT):]
            if not prefix and not rest:
                return Inst('print_int', line=lineno, var=1)
            if not rest and prefix and all(c == K_K for c in prefix):
                return Inst('print_int', line=lineno, var=prefix.count(K_K)+1)
            # rest가 ㅋ로만 구성 → 정수 출력
            if rest and all(c == K_K for c in rest):
                return Inst('print_int', line=lineno, var=rest.count(K_K)+1)
            return Inst('print_char', line=lineno, value=rest.strip())

        # 함수 호출
        if line.startswith(K_CALL):
            return Inst('call', line=lineno, name=line[len(K_CALL):].strip())

        # 대입 (엄)
        if K_ASSIGN in line:
            pos = line.index(K_ASSIGN)
            var_part = line[:pos]
            val_part = line[pos+1:]
            var_idx = var_part.count(K_K) or 1
            return Inst('assign', line=lineno, var=var_idx, value=val_part.strip())

        # ── 테이프 명령어 ──
        if line == K_TAPE_RIGHT:
            return Inst('tape_right', line=lineno)
        if line == K_TAPE_LEFT:
            return Inst('tape_left', line=lineno)
        if line == K_TAPE_INC:
            return Inst('tape_inc', line=lineno)
        if line == K_TAPE_DEC:
            return Inst('tape_dec', line=lineno)
        if line == K_TAPE_OUT:
            return Inst('tape_out', line=lineno)
        if line == K_TAPE_IN:
            return Inst('tape_in', line=lineno)
        if line == K_TAPE_LOOP_START:
            return Inst('tape_loop_start', line=lineno)
        if line == K_TAPE_LOOP_END:
            return Inst('tape_loop_end', line=lineno)

        raise SyntaxError(f"알 수 없는 명령어 (줄 {lineno}): {line}")

    # ── 실행 ──

    def run(self, source):
        self.parse(source)
        if self.debug:
            self._dump_ast()
        self.pc = 0
        steps = 0
        while self.pc < len(self.instructions):
            inst = self.instructions[self.pc]
            self.pc += 1
            if self.debug and inst.kind not in ('nop',):
                ln = inst.data.get('line', '?')
                print(f"  [pc={self.pc-1}, 줄 {ln}] {inst.kind} | {dict(sorted(self.memory.items()))}")
            self._exec(inst)
            steps += 1
            if steps > 100000:
                raise RecursionError("무한 루프 감지! (100,000 단계 초과)")

    def _exec(self, inst):
        k = inst.kind

        if k in ('nop', 'start'):
            return

        if k == 'exit':
            ret = self._val(inst.data['value'], "내아내임")
            if self.debug:
                print(f"\n[한남랭] 종료. 반환값: {ret}")
            sys.exit(ret)

        if k == 'input':
            try:
                val = int(input("입력: "))
            except (ValueError, EOFError):
                val = 0
            self.memory[inst.data['var']] = val

        elif k == 'jump':
            self.pc = self._val(inst.data['target'], "요이") - 1

        elif k == 'loop':
            # 자가 포함 루프 (함수 본체용)
            body = inst.data['body']
            condition = inst.data['condition']
            max_iter = 100000
            for _ in range(max_iter):
                for bi in body:
                    self._exec(bi)
                cond = self._val(condition, "루프 조건")
                if cond == 0:
                    break
            else:
                raise RecursionError("무한 루프 감지! (100,000 반복 초과)")

        elif k == 'loop_break':
            cond = self._val(inst.data['condition'], "루프 탈출")
            if cond == 0:
                return  # 탈출
            if self.loop_stack:
                self.pc = self.loop_stack[-1]  # 계속

        elif k == 'loop_start':
            self.loop_stack.append(self.pc)

        elif k == 'cond':
            if self._val(inst.data['condition'], "조건") == 0:
                self._exec_str(inst.data['command'])

        elif k == 'newline':
            if inst.data['suffix']:
                print(self._val(inst.data['suffix'], "티~원"), end='')
            print('\n' * (inst.data['count'] - 1), end='\n')

        elif k == 'print_int':
            print(self.memory.get(inst.data['var'], 0), end='')

        elif k == 'print_char':
            val = self._val(inst.data['value'], " kk이야")
            try:
                print(chr(val), end='')
            except (ValueError, OverflowError):
                print(val, end='')

        elif k == 'assign':
            self.memory[inst.data['var']] = self._val(inst.data['value'], "대입")

        elif k == 'call':
            name = inst.data['name']
            if name not in self.functions:
                raise SyntaxError(f"정의되지 않은 함수: '{name}' (줄 {inst.data['line']})")
            saved_pc = self.pc
            saved_loop = list(self.loop_stack)
            for fi in self.functions[name]:
                self._exec(fi)
            self.pc = saved_pc
            self.loop_stack = saved_loop

        # ── 테이프 명령어 ──
        elif k == 'tape_right':
            self.tape_ptr = (self.tape_ptr + 1) % 30000
        elif k == 'tape_left':
            self.tape_ptr = (self.tape_ptr - 1) % 30000
        elif k == 'tape_inc':
            self.tape[self.tape_ptr] = (self.tape[self.tape_ptr] + 1) % 256
        elif k == 'tape_dec':
            self.tape[self.tape_ptr] = (self.tape[self.tape_ptr] - 1) % 256
        elif k == 'tape_out':
            print(chr(self.tape[self.tape_ptr]), end='')
        elif k == 'tape_in':
            try:
                self.tape[self.tape_ptr] = ord(input()[0]) % 256
            except (IndexError, EOFError):
                self.tape[self.tape_ptr] = 0
        elif k == 'tape_loop':
            body = inst.data['body']
            max_iter = 1000000
            for _ in range(max_iter):
                if self.tape[self.tape_ptr] == 0:
                    break
                for bi in body:
                    self._exec(bi)
            else:
                raise RecursionError("테이프 루프 무한 반복!")

    def _exec_str(self, cmd):
        """조건부 실행용 문자열 명령어 처리"""
        cmd = cmd.strip()
        if not cmd:
            return
        # kk이야 출력
        if cmd == K_PRINT:
            print(self.memory.get(1, 0), end='')
            return
        if cmd.startswith(K_PRINT):
            rest = cmd[len(K_PRINT):]
            if not rest:
                print(self.memory.get(1, 0), end='')
            else:
                val = self._val(rest)
                try:
                    print(chr(val), end='')
                except (ValueError, OverflowError):
                    print(val, end='')
            return
        # 대입
        if K_ASSIGN in cmd:
            pos = cmd.index(K_ASSIGN)
            var_part = cmd[:pos]
            val_part = cmd[pos+1:]
            var_idx = var_part.count(K_K) or 1
            self.memory[var_idx] = self._val(val_part)
            return

    # ── 디버그 ──

    def _dump_ast(self):
        print("═══ AST ═══")
        for i, inst in enumerate(self.instructions):
            if inst.kind == 'nop':
                continue
            ln = inst.data.get('line', '?')
            d = {k: v for k, v in inst.data.items() if k != 'line'}
            print(f"  [{i:3d}] (줄 {ln:>3}) {inst.kind:12} {d}")
        print("═══ 실행 ═══")


# ══════════════════════════════════════════════════════════════
# 엔트리포인트
# ══════════════════════════════════════════════════════════════

def main():
    args = sys.argv[1:]
    debug = '--debug' in args
    ast_only = '--ast' in args
    repl = '--repl' in args
    args = [a for a in args if not a.startswith('--')]

    if repl:
        print("한남랭 REPL (v3.0)")
        print("종료: Ctrl+C 또는 'quit'")
        buf = []
        while True:
            try:
                line = input("한남> ").strip()
                if line == 'quit':
                    break
                buf.append(line)
                if line.startswith(K_EXIT):
                    code = '\n'.join(buf)
                    if not code.startswith(K_START):
                        code = K_START + '\n' + code
                    try:
                        HannamLang(debug=debug).run(code)
                    except SystemExit:
                        pass
                    except Exception as e:
                        print(f"오류: {e}")
                    buf = []
            except (EOFError, KeyboardInterrupt):
                print("\n종료합니다.")
                break
        return

    if not args:
        print("사용법: python hannam.py [옵션] <파일.한남>")
        print()
        print("옵션:")
        print("  --debug   실행 과정 단계별 출력")
        print("  --ast     파싱된 AST 출력 (실행 안 함)")
        print("  --repl    대화형 REPL 모드")
        sys.exit(1)

    try:
        with open(args[0], encoding='utf-8') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {args[0]}")
        sys.exit(1)

    interp = HannamLang(debug=debug)

    if ast_only:
        interp.parse(code)
        print(f"═══ AST ({args[0]}) ═══")
        interp._dump_ast()
        return

    interp.run(code)


if __name__ == '__main__':
    main()
