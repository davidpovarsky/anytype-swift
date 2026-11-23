# Explicit importlib.util dependency

The first actual current Release run exposed a missing explicit standard-library dependency. The common controller uses importlib.util.find_spec but imported only importlib. The one-line correction imports importlib.util before helpers can use it. Every function/class AST and every selector remains identical. The previous three focused controls remain retained and were not replayed. This source packet performs AST/static inverse checks only; no new host, product or Apple execution is claimed. Root retains the actual failed run and owns publication/retry.

The separate Page entrypoint already explicitly imports importlib.util, so its source is unchanged. Its future fixed common-source row must be rebound to this correction. No unrelated runtime or manifest is edited here.
