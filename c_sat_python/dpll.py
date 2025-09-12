import logging


# 赋值
def assign(x: int, _clauses: list[list[int]]) -> list[list[int]]:
    new_clauses = []
    for c in _clauses:
        if x in c:
            continue  # 子句被满足
        new_clause = []
        for l in c:
            if l != -x:
                new_clause.append(l)
        new_clauses.append(new_clause)
    return new_clauses


# 找到出现次数最多的文字
def find_literal(clauses: list[list[int]]) -> int:
    freq: dict[int, int] = dict()
    for c in clauses:
        for lit in c:
            freq[lit] = freq.get(lit, 0) + 1
    return max(freq.items(), key=lambda x: x[1])[0]


# dpll函数
def dpll_reduce(cur_literals: list[int], cur_clauses: list[list[int]]) -> list[int] | None:
    # logging.info(f"dpll_reduce, cur_literals: cnt={len(cur_literals)}, {cur_literals}")

    # 通过单子句规则化简
    while any(len(c) == 1 for c in cur_clauses):
        single_literal_clauses = []
        for c in cur_clauses:
            if len(c) == 1:
                single_literal_clauses.append(c)
        single_literal = single_literal_clauses[0][0]
        cur_literals.append(single_literal)
        cur_clauses = assign(single_literal, cur_clauses)

        if not cur_clauses:  # 所有子句被满足
            return cur_literals
        if [] in cur_clauses:  # 存在空子句（矛盾）
            return None

    # 判断是否结束
    if not cur_clauses:
        return cur_literals
    if [] in cur_clauses:
        return None

    # 寻找子句最多的文字
    next_ltl = find_literal(cur_clauses)

    # 赋值为true
    reduced_clauses_true = assign(next_ltl, cur_clauses)
    result = dpll_reduce(cur_literals + [next_ltl], reduced_clauses_true)
    if result:
        return result

    # 赋值为false
    reduced_clauses_false = assign(-next_ltl, cur_clauses)
    return dpll_reduce(cur_literals + [-next_ltl], reduced_clauses_false)
