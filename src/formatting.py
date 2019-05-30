import ast
import re


def expand_template(template, env=None, **kwargs):
    if not env:
        env = dict()
    env = {k.lower(): v for k, v in env.items()}
    env.update({k.lower(): v for k, v in kwargs.items()})

    funs = {}

    def get_names(expr):
        names = set()
        for node in ast.walk(expr):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                node.id = node.id.lower()
                names.add(node.id)
        return list(names)

    def mkfun(expression):
        key = ast.dump(expression)
        if key in funs:
            return funs[key]

        names = get_names(expression)
        body = expression.body

        args = [ast.arg(arg=name, annotation=None) for name in names]
        body = ast.Lambda(
            ast.arguments(args=args, defaults=[], kwonlyargs=[], kw_defaults=[]),
            body)

        expression.body = body
        ast.fix_missing_locations(expression)

        f = compile(expression, filename="<ast>", mode='eval')
        value = (eval(f), names)
        funs[key] = value
        return value

    def expand(src):
        ex = ast.parse(src, mode='eval')
        if not isinstance(ex, ast.Expression):
            return ''
        f, names = mkfun(ex)
        args = [str(env.get(name)) or '' for name in names]
        return f(*args)

    # TODO: do something smarter here for matching { }
    return re.sub(r'\${([^}]+)}', lambda m: expand(m.group(1)), template)


class Table(object):
    def __init__(self, *, width=0, colpadding=1, show_row_numbers=False):
        self.width = width
        self.sizes = [0] * width
        self.rows = []
        self.colpadding = colpadding
        self.headers = []
        self.show_row_numbers = show_row_numbers

    def add_row(self, *args):
        try:
            self._ensure_width(args)
            self._update_sizes(args)
            self.rows.append(tuple(args))
        except ValueError:
            if args:
                raise
            self.rows.append(tuple([''] * self.width))

    def _update_sizes(self, args):
        self.sizes = list(map(max, zip(self.sizes, map(len, args))))

    def _ensure_width(self, args):
        if not self.width:
            self.width = len(args)
            self.sizes = [0] * self.width
        if len(args) != self.width:
            raise ValueError('arguments list not the same width')

    def _format_row(self, args, sizes):
        gutter = ' ' * self.colpadding
        template = ['{:<{}}'] * len(args)
        template = (gutter + '|' + gutter).join(template)
        fmtargs = zip(args, sizes)
        return template.format(*[x for y in fmtargs for x in y])

    def _format_rule(self, sizes):
        line_width = len(self._format_row([''] * len(sizes), sizes))
        rule = ['-'] * line_width
        i = 0
        for j in sizes[:-1]:
            i += j + self.colpadding
            rule[i] = '+'
            i += 1 + self.colpadding
        return ''.join(rule)

    def __str__(self):
        output = ''
        sizes = self.sizes
        if self.show_row_numbers:
            sizes = [len(str(len(self.rows)))] + sizes

        if self.headers:
            headers = self.headers
            if self.show_row_numbers:
                headers = [''] + headers
            output += self._format_row(headers, sizes) + '\n'
            output += self._format_rule(sizes) + '\n'

        for i, row in enumerate(self.rows):
            if self.show_row_numbers:
                row = [i] + list(row)
            output += self._format_row(row, sizes) + '\n'

        return output.rstrip()

    def set_headers(self, *args):
        args = list(args)
        self._ensure_width(args)
        self._update_sizes(args)
        self.headers = args