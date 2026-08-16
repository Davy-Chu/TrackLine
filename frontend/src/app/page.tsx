import { environmentStatus } from "@/lib/health";

export default function Home() {
  return (
    <main>
      <p className="eyebrow">Trackline · Milestone 0</p>
      <h1>Development environment ready</h1>
      <p>{environmentStatus}</p>
    </main>
  );
}
