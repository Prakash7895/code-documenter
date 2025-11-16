from tree_sitter import Language

Language.build_library(
    "build/my-languages.so",
    [
        "vendor/tree-sitter-python",
        "vendor/tree-sitter-javascript",
        "vendor/tree-sitter-typescript/typescript",
        "vendor/tree-sitter-typescript/tsx",
        "vendor/tree-sitter-json",
    ],
)
print("Built build/my-languages.so")
