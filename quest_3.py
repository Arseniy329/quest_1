def solve(expression: str):
    def apply_op(operators, values):
        operator = operators.pop()
        right = values.pop()
        left = values.pop()
        if operator == '+':
            values.append(left + right)
        elif operator == '-':
            values.append(left - right)
        elif operator == '*':
            values.append(left * right)
        elif operator == '/':
            values.append(left / right)

    values = []
    operators = []
    precedence = {'+': 1, '-': 1, '*': 2, '/': 2}
    
    i = 0
    n = len(expression)

    while i < n:
        char = expression[i]

        if char == ' ':
            i += 1
            continue

        if char.isdigit():
            val = 0
            while i < n and expression[i].isdigit():
                val = (val * 10) + int(expression[i])
                i += 1
            values.append(val)
            continue

        if char == '(':
            operators.append(char)
        elif char == ')':
            while operators and operators[-1] != '(':
                apply_op(operators, values)
            operators.pop()
        elif char in precedence:
            while (operators and operators[-1] in precedence and 
                   precedence[operators[-1]] >= precedence[char]):
                apply_op(operators, values)
            operators.append(char)
            
        i += 1

    while operators:
        apply_op(operators, values)

    result = values[0]
    return int(result) if isinstance(result, float) and result.is_integer() else result


input_expression = input("Enter a mathematical expression: ")
print(solve(input_expression))