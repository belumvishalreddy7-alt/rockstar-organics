export interface TranslationFieldsOut { name?: string; short_description?: string; full_description?: string; benefits?: string; precautions?: string; }
export type ProductTranslations = Partial<Record<"te" | "hi" | "kn" | "ta", TranslationFieldsOut>>;

/** Falls back to the English column whenever the current language has no
 * owner-entered translation for this field (or the language is English
 * itself) - a partial translation should never show a blank instead of
 * the real, verified English text. */
export function localizedProductField<T extends Partial<Record<keyof TranslationFieldsOut, string | null>> & { translations: ProductTranslations }>(
  data: T, lang: string, field: keyof TranslationFieldsOut,
): string | null | undefined {
  if (lang === "en") return data[field];
  const translated = data.translations[lang as "te" | "hi" | "kn" | "ta"]?.[field];
  return translated || data[field];
}
