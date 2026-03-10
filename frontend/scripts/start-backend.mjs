import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawn, spawnSync } from 'node:child_process'

const currentDir = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(currentDir, '..', '..')
const backendDir = path.resolve(repoRoot, 'backend')
const port = process.env.COMPASSISTANT_BACKEND_PORT || '8000'

const candidates = []

if (process.env.COMPASSISTANT_BACKEND_PYTHON) {
  candidates.push({
    command: process.env.COMPASSISTANT_BACKEND_PYTHON,
    argsPrefix: [],
  })
}

const venvPython = path.resolve(
  backendDir,
  '.venv',
  process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
)
if (fs.existsSync(venvPython)) {
  candidates.push({ command: venvPython, argsPrefix: [] })
}

if (process.platform === 'win32') {
  candidates.push({ command: 'python', argsPrefix: [] })
  candidates.push({ command: 'py', argsPrefix: ['-3'] })
} else {
  candidates.push({ command: 'python3', argsPrefix: [] })
  candidates.push({ command: 'python', argsPrefix: [] })
}

function resolvePython() {
  for (const candidate of candidates) {
    try {
      const probe = spawnSync(candidate.command, [...candidate.argsPrefix, '--version'], {
        cwd: backendDir,
        stdio: 'ignore',
      })
      if (probe.status === 0) {
        return candidate
      }
    } catch {
      // Try the next candidate.
    }
  }
  throw new Error(
    'Unable to locate a Python interpreter for the backend. Set COMPASSISTANT_BACKEND_PYTHON if needed.',
  )
}

const python = resolvePython()
const child = spawn(
  python.command,
  [
    ...python.argsPrefix,
    '-m',
    'uvicorn',
    'app.main:app',
    '--host',
    '127.0.0.1',
    '--port',
    port,
  ],
  {
    cwd: backendDir,
    env: {
      ...process.env,
      RESEARCH_RUNTIME_MODE: process.env.RESEARCH_RUNTIME_MODE || 'mock',
      PYTHONIOENCODING: 'utf-8',
    },
    stdio: 'inherit',
  },
)

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal)
    return
  }
  process.exit(code ?? 0)
})
