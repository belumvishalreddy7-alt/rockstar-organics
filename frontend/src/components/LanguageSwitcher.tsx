import { useLanguage } from "../context/LanguageContext";
import { LANGUAGES, type Lang } from "../i18n/translations";

export function LanguageSwitcher() {
  const { language, setLanguage, t } = useLanguage();
  return (
    <select
      aria-label={t("language.label")}
      value={language}
      onChange={(e) => setLanguage(e.target.value as Lang)}
      className="language-switcher"
    >
      {LANGUAGES.map((l) => (
        <option key={l.code} value={l.code}>{l.nativeLabel}</option>
      ))}
    </select>
  );
}
