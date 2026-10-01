// HTML compiles pattern with UnicodeSets (v); a literal class hyphen must be escaped.
// Stable IDs also exclude the two URL dot-segments; canonical non-reserved IDs are unchanged.
export const IDENTIFIER_PATTERN = String.raw`(?!(?:\.|\.\.)$)[A-Za-z0-9:_.\-]+`
export const USERNAME_PATTERN = String.raw`[A-Za-z0-9_.\-]+`
