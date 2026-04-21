const vscode = require("vscode");
const client = require("./src/client");

function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand("aiCodeGen.generateFunction", cmdGenerateFunction),
    vscode.commands.registerCommand("aiCodeGen.generateClass", cmdGenerateClass),
    vscode.commands.registerCommand("aiCodeGen.generateTests", cmdGenerateTests),
    vscode.commands.registerCommand("aiCodeGen.validateCode", cmdValidateCode),
    vscode.commands.registerCommand("aiCodeGen.explainCode", cmdExplainCode)
  );
}

// ── Generate Function (Ctrl+Shift+K) ─────────────────────────────────────────
async function cmdGenerateFunction() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;

  const functionName = await vscode.window.showInputBox({
    prompt: "Function name",
    placeHolder: "e.g. calculate_discount",
  });
  if (!functionName) return;

  const description = await vscode.window.showInputBox({
    prompt: "What should this function do?",
    placeHolder: "e.g. Calculate discount percentage based on price and tier",
  });
  if (!description) return;

  const context = editor.document.getText(editor.selection) || "";

  await withProgress("Generating function...", async () => {
    const result = await client.generateFunction(functionName, description, context);
    await insertCode(editor, result.code);
    showResult(result);
  });
}

// ── Generate Class ────────────────────────────────────────────────────────────
async function cmdGenerateClass() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;

  const className = await vscode.window.showInputBox({
    prompt: "Class name",
    placeHolder: "e.g. UserRepository",
  });
  if (!className) return;

  const description = await vscode.window.showInputBox({
    prompt: "What does this class represent?",
    placeHolder: "e.g. Manages user CRUD operations against a database",
  });
  if (!description) return;

  const methodsInput = await vscode.window.showInputBox({
    prompt: "Methods to include (comma-separated, optional)",
    placeHolder: "e.g. get_by_id, create, update, delete",
  });
  const methods = methodsInput ? methodsInput.split(",").map((m) => m.trim()) : [];

  await withProgress("Generating class...", async () => {
    const result = await client.generateClass(className, description, methods);
    await insertCode(editor, result.code);
    showResult(result);
  });
}

// ── Generate Tests ────────────────────────────────────────────────────────────
async function cmdGenerateTests() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;

  const sourceCode = editor.document.getText(editor.selection);
  if (!sourceCode) {
    vscode.window.showWarningMessage("Select the code you want to generate tests for first.");
    return;
  }

  await withProgress("Generating tests...", async () => {
    const result = await client.generateTests(sourceCode);
    await insertCode(editor, result.code);
    showResult(result);
  });
}

// ── Validate Code ─────────────────────────────────────────────────────────────
async function cmdValidateCode() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;

  const code = editor.document.getText(editor.selection) || editor.document.getText();
  if (!code.trim()) {
    vscode.window.showWarningMessage("No code to validate.");
    return;
  }

  await withProgress("Validating...", async () => {
    const result = await client.validateCode(code);
    const icon = result.is_valid ? "✅" : "❌";
    const issues = [
      ...result.security_issues.map((i) => `🔒 ${i}`),
      ...result.quality_notes.map((n) => `💡 ${n}`),
    ];
    const detail = issues.length ? issues.join("\n") : "No issues found.";
    const msg = `${icon} Confidence: ${result.confidence_score}%  |  Quality: ${result.quality_score}%`;
    if (result.is_valid) {
      vscode.window.showInformationMessage(msg, { detail, modal: false });
    } else {
      vscode.window.showWarningMessage(msg, { detail, modal: true });
    }
  });
}

// ── Explain Code ──────────────────────────────────────────────────────────────
async function cmdExplainCode() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;

  const code = editor.document.getText(editor.selection) || editor.document.getText();
  if (!code.trim()) {
    vscode.window.showWarningMessage("No code selected.");
    return;
  }

  await withProgress("Explaining...", async () => {
    const result = await client.explainCode(code);
    const panel = vscode.window.createWebviewPanel(
      "aiExplanation",
      "AI Explanation",
      vscode.ViewColumn.Beside,
      {}
    );
    panel.webview.html = `<html><body style="font-family:sans-serif;padding:16px;white-space:pre-wrap">${escapeHtml(result.explanation)}</body></html>`;
  });
}

// ── Helpers ───────────────────────────────────────────────────────────────────
async function insertCode(editor, code) {
  await editor.edit((editBuilder) => {
    if (!editor.selection.isEmpty) {
      editBuilder.replace(editor.selection, code);
    } else {
      const end = editor.document.lineAt(editor.document.lineCount - 1).range.end;
      editBuilder.insert(end, "\n\n" + code);
    }
  });
}

function showResult(result) {
  const icon = result.validation.is_valid ? "✅" : "⚠️";
  vscode.window.showInformationMessage(
    `${icon} Generated in ${result.latency_ms.toFixed(0)}ms  |  Confidence: ${result.confidence_score}%  |  Tokens: ${result.tokens_used}`
  );
}

async function withProgress(title, fn) {
  return vscode.window.withProgress(
    { location: vscode.ProgressLocation.Notification, title, cancellable: false },
    async () => {
      try {
        const isUp = await client.healthCheck();
        if (!isUp) {
          vscode.window.showErrorMessage("AI Code Generator server is not running. Start it with: python main.py");
          return;
        }
        await fn();
      } catch (err) {
        vscode.window.showErrorMessage(`Error: ${err.message}`);
      }
    }
  );
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function deactivate() {}

module.exports = { activate, deactivate };
