#!/bin/bash
cd /home/kavia/workspace/code-generation/fullstack-todo-application-40750-40759/backend_fastapi
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

