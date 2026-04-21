const BASE_URL = "http://localhost:8000";

async function post(path, body) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(err.detail || response.statusText);
  }
  return response.json();
}

async function generateFunction(functionName, description, context = "") {
  return post("/generate/function", { function_name: functionName, description, context });
}

async function generateClass(className, description, methods = []) {
  return post("/generate/class", { class_name: className, description, methods });
}

async function generateTests(sourceCode) {
  return post("/generate/tests", { source_code: sourceCode });
}

async function validateCode(code) {
  return post("/validate", { code });
}

async function explainCode(sourceCode) {
  return post("/explain", { source_code: sourceCode });
}

async function healthCheck() {
  const r = await fetch(`${BASE_URL}/health`);
  return r.ok;
}

module.exports = { generateFunction, generateClass, generateTests, validateCode, explainCode, healthCheck };
