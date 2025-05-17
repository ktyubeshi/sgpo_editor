レガシー互換のためのその場しのぎのコードは書かないでください。
変更の適用中にスコープ外のコードとの非互換でコードが壊れる場合、ToDo.mdを更新し、次のタスクとして記録を残してください。

LinterにはRuffを使用してください。
`uv run ruff check --fix`

静的解析にはtyを使用してください
`uv run ty check src --exit-zero`

テストにはpytestを使用してください
`uv run pytest`
