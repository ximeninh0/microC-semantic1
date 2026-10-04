from __future__ import annotations

from ast_nodes import Program, TypeName
from semantic_errors import SemanticDiagnostic, SemanticError, SemanticErrorKind
from symbols import FunctionSymbol, SymbolKind


def resolve_names(program: Program) -> None:
    """Construa escopos, símbolos e vínculos entre usos e declarações."""
    functions: dict[str, FunctionSymbol] = {}
    diagnostics: list[SemanticDiagnostic] = []

    # 1. Colete todas as assinaturas de função.
    for function in program.functions:
        function_symbol = FunctionSymbol(
            name=function.name,
            kind=SymbolKind.FUNCTION,
            type=function.return_type,
            declaration=function,
            parameter_types=tuple(p.type for p in function.parameters),
        )
        function.metadata["symbol"] = function_symbol

        # se já tem a função acumula o erro e não duplica
        if function.name in functions:
            diagnostics.append(SemanticDiagnostic(
                kind=SemanticErrorKind.DUPLICATE_FUNCTION,
                message=f"Função '{function.name}' já declarada",
                span=function.span,
            ))
        else:
            functions[function.name] = function_symbol

    # 2. Valide a existência e a assinatura de main.
    main = functions.get("main")
    if main is None: # caso não tenha main
        diagnostics.append(SemanticDiagnostic(
            kind=SemanticErrorKind.INVALID_MAIN,
            message="A função 'main' não foi encontrada",
            span=program.span,
        ))
    # se o tipo de retorno não for int
    if main is not None and (main.type is not TypeName.INT): # se o tipo de retorno não for int
        diagnostics.append(SemanticDiagnostic(
            kind=SemanticErrorKind.INVALID_MAIN,
            message="A função 'main' deve ter return type 'int'",
            span=main.declaration.span,
        ))
    if main is not None and (len(main.parameter_types) != 0): # se tiver parametros
        diagnostics.append(SemanticDiagnostic(
            kind=SemanticErrorKind.INVALID_MAIN,
            message="A função 'main' não deve ter parâmetros",
            span=main.declaration.span,
        ))

    # 3. Percorra os corpos em ordem, criando um escopo para cada bloco.
    # 4. Anote declarações, usos e blocos na AST.
    raise NotImplementedError("implemente a resolução dos corpos")

    # 5. Acumule os diagnósticos desta passagem antes de lançar SemanticError.
    if diagnostics:
        raise SemanticError(diagnostics)
