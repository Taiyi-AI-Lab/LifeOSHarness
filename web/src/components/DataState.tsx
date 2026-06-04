type DataStateProps = {
  title: string;
  detail?: string;
  action?: () => void;
};

export function EmptyState({ title, detail }: DataStateProps) {
  return (
    <div className="data-state">
      <strong>{title}</strong>
      {detail ? <p>{detail}</p> : null}
    </div>
  );
}

export function ErrorState({ title, detail, action }: DataStateProps) {
  return (
    <div className="data-state data-state--error">
      <strong>{title}</strong>
      {detail ? <p>{detail}</p> : null}
      {action ? (
        <button className="button button--secondary" type="button" onClick={action}>
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function LoadingState({ title = "Loading" }: { title?: string }) {
  return (
    <div className="skeleton-stack" aria-label={title}>
      <span />
      <span />
      <span />
    </div>
  );
}
