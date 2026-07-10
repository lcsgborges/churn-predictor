# Demonstração

Vídeo demonstrando o sistema funcionando em casos de uso reais, seguindo o fluxo de um usuário típico
do início ao resultado.

!!! info "Vídeo"
    O roteiro está pronto; o link será adicionado quando a gravação for publicada.

## Roteiro

1. Carregar o perfil fictício **"Exemplo: alto risco"** → **Analisar cliente** → mostrar probabilidade, fatores SHAP e a
   ação de retenção recomendada.
2. Usar o **Chat de retenção** para perguntar sobre o cliente carregado.
3. Tentar um **jailbreak** ("ignore suas instruções...") → o guardrail bloqueia e reorienta.
4. Chamar a **API pública** via `curl` em `/api/predict`.
5. Abrir a aba **Monitoramento** (latência, custo, taxa de fallback e de guardrails).
