export default function Loading() {
  return (
    <main className="min-h-screen bg-slate-50 p-6 dark:bg-slate-950">
      <div className="mx-auto max-w-7xl animate-pulse space-y-6">
        <div className="h-10 w-72 rounded-xl bg-slate-200 dark:bg-slate-800" />
        <div className="h-20 rounded-2xl bg-slate-200 dark:bg-slate-800" />
        <div className="grid gap-4 md:grid-cols-5">
          {Array.from({ length: 5 }, (_, index) => (
            <div key={index} className="h-36 rounded-2xl bg-slate-200 dark:bg-slate-800" />
          ))}
        </div>
      </div>
    </main>
  );
}
