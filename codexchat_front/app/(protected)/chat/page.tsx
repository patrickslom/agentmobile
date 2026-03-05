export default function ChatPage() {
  return (
    <section className="mx-auto w-full max-w-4xl space-y-4">
      <div className="rounded-2xl border border-border bg-muted p-4 sm:p-5">
        <p className="text-xs font-semibold tracking-[0.14em] uppercase text-muted-foreground">
          User
        </p>
        <p className="mt-2 text-sm text-foreground sm:text-base">
          Sketch a two-pane shell that we can use for streaming chat and
          settings pages.
        </p>
      </div>

      <div className="rounded-2xl border border-border bg-background p-4 sm:p-5">
        <p className="text-xs font-semibold tracking-[0.14em] uppercase text-muted-foreground">
          Assistant
        </p>
        <div className="mt-2 space-y-3 text-sm sm:text-base">
          <p>
            The app now uses a sidebar and conversation pane structure that
            mirrors production chat workflows.
          </p>
          <p>Next integration point:</p>
          <pre>
            <code>{`{
  "event": "send_message",
  "conversationId": "placeholder-id",
  "content": "Hello from the new shell"
}`}</code>
          </pre>
        </div>
      </div>
    </section>
  );
}
