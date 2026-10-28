import { useState } from "react"
import { MessageCircleQuestionIcon } from "lucide-react"
import { Button } from "@components/ui/button"
import { Input } from "@components/ui/input"
import MarkdownRenderer from "@components/ui/markdown"
import { cn } from "@lib/utils"
import _ from "@lib/translate"
import { hasDetails, togglePick, type AskedQuestion, type Draft, type } from "./questionAnswers"

interface ChatbotQuestionItemProps {
    item: AskedQuestion
    draft: Draft
    onChange: (change: (draft: Draft) => Draft) => void
    busy: boolean
}

/** One open question: its choices (with a preview beside them when they have one) and a box for the user's own answer. */
export const ChatbotQuestionItem = ({ item, draft, onChange, busy }: ChatbotQuestionItemProps) => {
    const multiple = Boolean(item.multiple)
    const [focused, setFocused] = useState<string | null>(null)
    const shown = item.options.find((option) => option.label === (focused ?? draft.picked[0]))
    const pick = (label: string) => onChange((current) => togglePick(current, label, multiple))

    return (
        <>
            {hasDetails(item) ? (
                <div className="grid gap-3 md:grid-cols-[minmax(0,15rem)_minmax(0,1fr)]">
                    <div className="flex flex-col gap-1.5" onMouseLeave={() => setFocused(null)}>
                        {item.options.map((option) => (
                            <Button key={option.label} size="sm" variant={draft.picked.includes(option.label) ? "solid" : "outline"} aria-pressed={draft.picked.includes(option.label)} disabled={busy}
                                className="h-auto flex-col items-start gap-0 whitespace-normal py-1.5 text-left" onClick={() => pick(option.label)}
                                onMouseEnter={() => setFocused(option.label)} onFocus={() => setFocused(option.label)}>
                                <span>{option.label}</span>
                                {option.description && <span className="text-xs font-normal opacity-70">{option.description}</span>}
                            </Button>
                        ))}
                    </div>
                    <div className={cn("min-h-16 rounded-md border border-outline-gray-2 bg-surface-gray-1 p-2 text-p-sm text-ink-gray-8", !shown?.preview && "flex items-center text-ink-gray-5")}>
                        {shown?.preview ? <MarkdownRenderer content={shown.preview} className="tiptap chatbot-markdown" allowHtml={false} /> : _("Point at a choice to see a preview.")}
                    </div>
                </div>
            ) : (
                <div className="flex flex-wrap gap-2">
                    {item.options.map((option) => (
                        <Button key={option.label} size="sm" variant={draft.picked.includes(option.label) ? "solid" : "outline"} aria-pressed={draft.picked.includes(option.label)} disabled={busy} onClick={() => pick(option.label)}>{option.label}</Button>
                    ))}
                </div>
            )}
            <Input value={draft.typed} disabled={busy} placeholder={multiple ? _("Add your own…") : _("Or type your own answer…")}
                aria-label={_("Your own answer")} onChange={(event) => onChange((current) => type(current, event.target.value, multiple))} />
        </>
    )
}

/** The question itself, with the mark that tells it apart from the AI's text. */
export const QuestionHeading = ({ text }: { text: string }) => (
    <div className="flex items-start gap-2 text-p-base font-medium text-ink-gray-8">
        <MessageCircleQuestionIcon className="mt-0.5 size-4 shrink-0 text-ink-blue-3" />
        <span className="whitespace-pre-line">{text}</span>
    </div>
)
