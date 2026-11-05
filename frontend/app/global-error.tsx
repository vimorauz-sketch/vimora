"use client";

export default function GlobalError({ reset }: { error: Error; reset: () => void }) {
  return (
    <html lang="uz" data-theme="dark">
      <body style={{ background: "#11110F", color: "#F5F1E8", fontFamily: "system-ui", padding: 48 }}>
        <h1 style={{ fontSize: 28 }}>500</h1>
        <p>Something went wrong. / Xatolik yuz berdi. / Произошла ошибка.</p>
        <button onClick={reset} style={{ marginTop: 16, background: "#D6F36A", color: "#11110F", padding: "10px 16px", border: 0, borderRadius: 6 }}>Retry</button>
      </body>
    </html>
  );
}
