import { useState } from "react"
import { MessageCircleQuestionIcon } from "lucide-react"
import LinkFieldCombobox from "@components/common/LinkFieldComboBox/LinkFieldCombobox"
import { Button } from "@components/ui/button"
import { Input } from "@components/ui/input"
import MarkdownRenderer from "@components/ui/markdown"
import _ from "@lib/translate"
import { hasDetails, hasPreview, togglePick, type AskedOption, type AskedQuestion, type Draft, type } from "./questionAnswers"

interface ChatbotQuestionItemProps {
    item: AskedQuestion
    draft: Draft
    onChange: (change: (draft: Draft) => Draft) => void
    /** Called after a single-choice pick, so a stepper can move on. */
    onPicked?: () => void
    busy: boolean
}

/** The question itself, with the mark that tells it apart from the AI's text and, beside it, whatever `children` the card puts there (the arrows). */
export const QuestionHeading = ({ text, children }: { text: string; children?: React.ReactNode }) => (
    <div className="flex items-start gap-2 text-p-base font-medium text-ink-gray-8">
        <MessageCircleQuestionIcon className="mt-0.5 size-4 shrink-0 text-ink-blue-3" />
        <span className="flex-1 whitespace-pre-line">{text}</span>
        {children}
    </div>
)

/** One open question: its choices, an "Other…" for the user's own words (a text box straight away when there are no choices). */
export const ChatbotQuestionItem = ({ item, draft, onChange, onPicked, busy }: ChatbotQuestionItemProps) => {
    const multiple = Boolean(item.multiple)
    const [otherOpen, setOtherOpen] = useState(item.options.length === 0 || Boolean(draft.typed))
    const [focused, setFocused] = useState<string | null>(null)
    const isPicked = (option: AskedOption) => draft.picked.includes(option.label)
    const shown = item.options.find((option) => option.label === (focused ?? draft.picked[0]))

    const pick = (label: string) => {
        onChange((current) => togglePick(current, label, multiple))
        if (!multiple && !draft.picked.includes(label)) onPicked?.()
    }
    const toggleOther = () => {
        if (otherOpen) onChange((current) => type(current, "", multiple))
        setOtherOpen(!otherOpen)
    }
    const choice = (option: AskedOption, listed: boolean) => (
        <Button key={option.label} size="sm" variant={isPicked(option) ? "solid" : "outline"} aria-pressed={isPicked(option)} disabled={busy}
            className={listed ? "h-auto flex-col items-start gap-0 whitespace-normal py-1.5 text-left" : undefined}
            onClick={() => pick(option.label)} onMouseEnter={() => setFocused(option.label)} onFocus={() => setFocused(option.label)}>
            <span>{option.label}</span>
            {listed && option.description && <span className="text-xs font-normal opacity-70">{option.description}</span>}
        </Button>
    )
    const other = item.options.length > 0 && (
        <Button size="sm" variant={otherOpen ? "solid" : "outline"} aria-pressed={otherOpen} disabled={busy} onClick={toggleOther}>{_("Other…")}</Button>
    )

    if (item.link_to) {
        return <LinkFieldCombobox doctype={item.link_to} value={draft.typed} disabled={busy} hideCreate clearable onChange={(value) => onChange((current) => type(current, value, false))} />
    }

    return (
        <>
            {hasDetails(item) ? (
                <div className={hasPreview(item) ? "grid gap-3 md:grid-cols-[minmax(0,15rem)_minmax(0,1fr)]" : ""}>
                    <div className="flex flex-col gap-1.5" onMouseLeave={() => setFocused(null)}>
                        {item.options.map((option) => choice(option, true))}
                        {other}
                    </div>
                    {hasPreview(item) && (
                        <div className="min-h-16 rounded-md border border-outline-gray-2 bg-surface-gray-1 p-2 text-p-sm text-ink-gray-8">
                            {shown?.preview ? <MarkdownRenderer content={shown.preview} className="tiptap chatbot-markdown" allowHtml={false} /> : <span className="text-ink-gray-5">{_("Point at a choice to see a preview.")}</span>}
                        </div>
                    )}
                </div>
            ) : (
                <div className="flex flex-wrap gap-2">{item.options.map((option) => choice(option, false))}{other}</div>
            )}
            {otherOpen && (
                <Input autoFocus={item.options.length > 0} value={draft.typed} disabled={busy} aria-label={_("Your own answer")}
                    placeholder={multiple ? _("Add your own…") : _("Type your answer…")} onChange={(event) => onChange((current) => type(current, event.target.value, multiple))} />
            )}
        </>
    )
}
