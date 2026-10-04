from __future__ import annotations

from ast_nodes import Program
from ast_nodes import (
    Assignment,
    BinaryExpr,
    BinaryOperator,
    Block,
    BoolLiteral,
    CallExpr,
    CallStmt,
    Expr,
    IdentifierExpr,
    IfStmt,
    IntLiteral,
    PrintStmt,
    ReturnStmt,
    Stmt,
    TypeName,
    UnaryExpr,
    UnaryOperator,
    VarDecl,
    WhileStmt,
)
from semantic_errors import SemanticDiagnostic, SemanticError, SemanticErrorKind
from symbols import FunctionSymbol

MAX_INT = (1 << 63) - 1

ARITHMETIC_OPS = {
    BinaryOperator.ADD,
    BinaryOperator.SUBTRACT,
    BinaryOperator.MULTIPLY,
    BinaryOperator.DIVIDE,
    BinaryOperator.REMAINDER,
}

RELATIONAL_OPS = {
    BinaryOperator.LESS,
    BinaryOperator.LESS_EQUAL,
    BinaryOperator.GREATER,
    BinaryOperator.GREATER_EQUAL,
}

EQUALITY_OPS = {
    BinaryOperator.EQUAL,
    BinaryOperator.NOT_EQUAL,
}

LOGICAL_OPS = {
    BinaryOperator.LOGICAL_AND,
    BinaryOperator.LOGICAL_OR,
}


def check_types(program: Program) -> None:
    """Determine tipos de expressões e valide seus contextos."""

    # 1. Use os símbolos anexados pela resolução de nomes.
    # 2. Determine cada expressão de baixo para cima.
    # 3. Valide operadores, chamadas, comandos e declarações.
    # 4. Anote expressões válidas e acumule os diagnósticos da passagem.
    diagnostics: list[SemanticDiagnostic] = []

    def type_of_expr(expr: Expr) -> TypeName | None:
        if isinstance(expr, IntLiteral):
            if expr.value < 0 or expr.value > MAX_INT:
                diagnostics.append(
                    SemanticDiagnostic(
                        kind=SemanticErrorKind.INTEGER_LITERAL_OUT_OF_RANGE,
                        message=f"Literal inteiro '{expr.value}' fora do intervalo [0, {MAX_INT}]",
                        span=expr.span,
                    )
                )
                return None
            expr.metadata["type"] = TypeName.INT
            return TypeName.INT

        if isinstance(expr, BoolLiteral):
            expr.metadata["type"] = TypeName.BOOL
            return TypeName.BOOL

        if isinstance(expr, IdentifierExpr):
            symbol = expr.metadata.get("symbol")
            if symbol is not None:
                expr.metadata["type"] = symbol.type
                return symbol.type
            return None

        if isinstance(expr, UnaryExpr):
            operand_type = type_of_expr(expr.operand)
            if operand_type is None:
                return None

            if expr.operator == UnaryOperator.NEGATE:
                if operand_type != TypeName.INT:
                    diagnostics.append(
                        SemanticDiagnostic(
                            kind=SemanticErrorKind.INVALID_UNARY_OPERAND,
                            message=f"Operador '-' unário exige 'int', recebeu '{operand_type.value}'",
                            span=expr.span,
                        )
                    )
                    return None
                expr.metadata["type"] = TypeName.INT
                return TypeName.INT

            if expr.operator == UnaryOperator.NOT:
                if operand_type != TypeName.BOOL:
                    diagnostics.append(
                        SemanticDiagnostic(
                            kind=SemanticErrorKind.INVALID_UNARY_OPERAND,
                            message=f"Operador '!' exige 'bool', recebeu '{operand_type.value}'",
                            span=expr.span,
                        )
                    )
                    return None
                expr.metadata["type"] = TypeName.BOOL
                return TypeName.BOOL

            return None

        if isinstance(expr, BinaryExpr):
            left_type = type_of_expr(expr.left)
            right_type = type_of_expr(expr.right)

            if left_type is None or right_type is None:
                return None

            op = expr.operator
            if op in ARITHMETIC_OPS:
                if left_type == TypeName.INT and right_type == TypeName.INT:
                    expr.metadata["type"] = TypeName.INT
                    return TypeName.INT
            elif op in RELATIONAL_OPS:
                if left_type == TypeName.INT and right_type == TypeName.INT:
                    expr.metadata["type"] = TypeName.BOOL
                    return TypeName.BOOL
            elif op in EQUALITY_OPS:
                if (left_type == TypeName.INT and right_type == TypeName.INT) or (
                    left_type == TypeName.BOOL and right_type == TypeName.BOOL
                ):
                    expr.metadata["type"] = TypeName.BOOL
                    return TypeName.BOOL
            elif op in LOGICAL_OPS:
                if left_type == TypeName.BOOL and right_type == TypeName.BOOL:
                    expr.metadata["type"] = TypeName.BOOL
                    return TypeName.BOOL

            diagnostics.append(
                SemanticDiagnostic(
                    kind=SemanticErrorKind.INVALID_BINARY_OPERANDS,
                    message=(
                        f"Operador '{op.value}' não suporta operandos "
                        f"'{left_type.value}' e '{right_type.value}'"
                    ),
                    span=expr.span,
                )
            )
            return None

        if isinstance(expr, CallExpr):
            for arg in expr.arguments:
                type_of_expr(arg)

            symbol = expr.metadata.get("symbol")
            if isinstance(symbol, FunctionSymbol):
                if symbol.type != TypeName.VOID:
                    expr.metadata["type"] = symbol.type
                return symbol.type
            return None

        return None

    def check_stmt(stmt: Stmt) -> None:
        if isinstance(stmt, Block):
            for s in stmt.statements:
                check_stmt(s)

        elif isinstance(stmt, VarDecl):
            if stmt.type == TypeName.VOID:
                diagnostics.append(
                    SemanticDiagnostic(
                        kind=SemanticErrorKind.VOID_VARIABLE,
                        message=f"Variável '{stmt.name}' não pode ser do tipo 'void'",
                        span=stmt.span,
                    )
                )
            if stmt.initializer is not None:
                type_of_expr(stmt.initializer)

        elif isinstance(stmt, Assignment):
            type_of_expr(stmt.target)
            type_of_expr(stmt.value)

        elif isinstance(stmt, CallStmt):
            type_of_expr(stmt.call)
            symbol = stmt.call.metadata.get("symbol")
            if isinstance(symbol, FunctionSymbol) and symbol.type == TypeName.VOID:
                stmt.call.metadata["type"] = TypeName.VOID

        elif isinstance(stmt, IfStmt):
            type_of_expr(stmt.condition)
            check_stmt(stmt.then_block)
            if stmt.else_block is not None:
                check_stmt(stmt.else_block)

        elif isinstance(stmt, WhileStmt):
            type_of_expr(stmt.condition)
            check_stmt(stmt.body)

        elif isinstance(stmt, ReturnStmt):
            if stmt.value is not None:
                type_of_expr(stmt.value)

        elif isinstance(stmt, PrintStmt):
            for item in stmt.items:
                if isinstance(item, Expr):
                    type_of_expr(item)

    for function in program.functions:
        for param in function.parameters:
            if param.type == TypeName.VOID:
                diagnostics.append(
                    SemanticDiagnostic(
                        kind=SemanticErrorKind.VOID_PARAMETER,
                        message=f"Parâmetro '{param.name}' não pode ser do tipo 'void'",
                        span=param.span,
                    )
                )

        check_stmt(function.body)

    if diagnostics:
        raise SemanticError(diagnostics)
