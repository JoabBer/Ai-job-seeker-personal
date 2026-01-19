import { useState } from "react";

const API_BASE = "http://127.0.0.1:8000";
const UPLOAD_PATH = "/UploadResume"; // match your FastAPI route

export default function App() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("");
  const [jobs, setJobs] = useState([]);
  const [raw, setRaw] = useState("");

  const upload = async () => {
    if (!file) return;

    setStatus("Uploading...");
    setJobs([]);
    setRaw("");

    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch(`${API_BASE}${UPLOAD_PATH}`, {
        method: "POST",
        body: form,
      });

      const data = await res.json();

      if (!res.ok) {
        setStatus("Error");
        setRaw(JSON.stringify(data, null, 2));
        return;
      }

      setStatus("Done");

      const analysis = data.analysis;
      try {
        const parsed = JSON.parse(analysis);
        setJobs(parsed.suitable_jobs || []);
        setRaw(JSON.stringify(parsed, null, 2));
      } catch {
        setRaw(analysis);
      }
    } catch (err) {
      setStatus("Backend not running");
      setRaw(String(err));
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: "40px auto", fontFamily: "sans-serif" }}>
      <h1>Resume Job Matcher</h1>
      <input type="file" accept="application/pdf" onChange={e => setFile(e.target.files[0])} />
      <button onClick={upload} disabled={!file}>Find Jobs</button>

      <p>{status}</p>

      {jobs.length > 0 && (
        <>
          <h2>Top Matches</h2>
          {jobs.map((j, i) => (
            <div key={i} style={{ border: "1px solid #ccc", padding: 10, margin: 10 }}>
              <b>{j.title}</b><br/>
              {j.company} – {j.location}<br/>
              <a href={j.url} target="_blank">View Job</a>
            </div>
          ))}
        </>
      )}

      {raw && (
        <>
          <h3>Raw Output</h3>
          <pre>{raw}</pre>
        </>
      )}
    </div>
  );
}
