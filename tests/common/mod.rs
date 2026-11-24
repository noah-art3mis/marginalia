//! Shared helpers: every test drives the real `marginalia` binary, as an agent would.
#![allow(dead_code)]

use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

use serde_json::Value;
use tempfile::TempDir;

pub fn run(cwd: &Path, args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_marginalia"))
        .current_dir(cwd)
        .args(args)
        .output()
        .expect("marginalia binary runs")
}

/// Run a command that must succeed and return its stdout.
pub fn ok(cwd: &Path, args: &[&str]) -> String {
    let out = run(cwd, args);
    assert!(
        out.status.success(),
        "{args:?} failed: {}",
        String::from_utf8_lossy(&out.stderr)
    );
    String::from_utf8(out.stdout).unwrap()
}

/// Run a command that must fail cleanly and return its error text.
pub fn err(cwd: &Path, args: &[&str]) -> String {
    let out = run(cwd, args);
    let stderr = String::from_utf8(out.stderr).unwrap();
    assert_eq!(
        out.status.code(),
        Some(1),
        "{args:?} should fail; stdout: {}",
        String::from_utf8_lossy(&out.stdout)
    );
    assert!(stderr.starts_with("Error: "), "unexpected error output: {stderr}");
    assert!(!stderr.contains("panicked"), "a panic is not a clean error: {stderr}");
    stderr
}

pub fn json(cwd: &Path, args: &[&str]) -> Value {
    serde_json::from_str(&ok(cwd, args)).expect("stdout is JSON")
}

/// A temporary folder holding `draft.md`.
pub struct Draft {
    pub dir: TempDir,
    pub path: PathBuf,
}

impl Draft {
    pub fn new(text: &str) -> Self {
        Self::bytes(text.as_bytes())
    }

    pub fn bytes(text: &[u8]) -> Self {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("draft.md");
        fs::write(&path, text).unwrap();
        Draft { dir, path }
    }

    /// A draft with an active pass of the given type.
    pub fn with_pass(text: &str, pass_type: &str) -> Self {
        let draft = Self::new(text);
        draft.ok(&["versions", "start"], &["--type", pass_type]);
        draft
    }

    pub fn root(&self) -> &Path {
        self.dir.path()
    }

    pub fn workspace(&self) -> PathBuf {
        self.root().join(".marginalia").join("draft.md")
    }

    pub fn read(&self) -> String {
        fs::read_to_string(&self.path).unwrap()
    }

    pub fn write(&self, text: &str) {
        fs::write(&self.path, text).unwrap();
    }

    fn args<'a>(&'a self, command: &[&'a str], rest: &[&'a str]) -> Vec<&'a str> {
        let mut args = command.to_vec();
        args.push(self.path.to_str().unwrap());
        args.extend_from_slice(rest);
        args
    }

    /// Run `command DOCUMENT rest...`, requiring success.
    pub fn ok(&self, command: &[&str], rest: &[&str]) -> String {
        ok(self.root(), &self.args(command, rest))
    }

    pub fn err(&self, command: &[&str], rest: &[&str]) -> String {
        err(self.root(), &self.args(command, rest))
    }

    pub fn json(&self, command: &[&str], rest: &[&str]) -> Value {
        let mut rest = rest.to_vec();
        rest.push("--json");
        json(self.root(), &self.args(command, &rest))
    }

    fn payload(&self, payload: &Value) -> String {
        let file = self.root().join("payload.json");
        fs::write(&file, payload.to_string()).unwrap();
        file.to_str().unwrap().to_owned()
    }

    /// Submit a proposal: `Ok(proposal)` or `Err(error text)`.
    pub fn submit(&self, payload: Value) -> Result<Value, String> {
        let file = self.payload(&payload);
        let out = run(self.root(), &self.args(&["review", "submit"], &["--file", &file, "--json"]));
        if out.status.success() {
            Ok(serde_json::from_slice(&out.stdout).unwrap())
        } else {
            Err(String::from_utf8(out.stderr).unwrap())
        }
    }

    pub fn submit_ok(&self, payload: Value) -> String {
        let proposal = self.submit(payload).expect("proposal accepted for review");
        proposal["id"].as_str().unwrap().to_owned()
    }

    pub fn revise(&self, id: &str, payload: Value) -> Value {
        let file = self.payload(&payload);
        self.json(&["review", "revise"], &[id, "--file", &file])
    }

    pub fn status_of(&self, id: &str) -> String {
        self.json(&["review", "show"], &[id])["status"].as_str().unwrap().to_owned()
    }

    pub fn write_workspace(&self, relative: &str, value: &Value) {
        let path = self.workspace().join(relative);
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(path, serde_json::to_string_pretty(value).unwrap()).unwrap();
    }

    pub fn read_workspace(&self, relative: &str) -> Value {
        serde_json::from_str(&fs::read_to_string(self.workspace().join(relative)).unwrap()).unwrap()
    }
}
