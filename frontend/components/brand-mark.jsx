export function BrandMark({ compact = false }) {
  return (
    <div className={`brand ${compact ? "brand-compact" : ""}`}>
      <span className="brand-mark" aria-hidden="true">
        <span />
        <span />
      </span>
      {!compact && (
        <span className="brand-copy">
          <strong>Aegis</strong>
          <small>AUTH CONTROL</small>
        </span>
      )}
    </div>
  );
}
