import { useState } from "react"
import { ChevronDownIcon, ChevronLeftIcon, ChevronRightIcon, CircleCheckIcon, CircleSlashIcon } from "lucide-react"
import { Badge } from "@components/ui/badge"
import { Button } from "@components/ui/button"
import _ from "@lib/translate"
import { cn } from "@lib/utils"
import { ChatbotQuestionItem, QuestionHeading } from "./ChatbotQuestionItem"
import { allAnswers, emptyDraft, hasAnyAnswer, nextToAnswer, type AskedQuestion, type Draft } from "./questionAnswers"
import { useAnswerChatbotQuestion } from "./useChatbotChat"
import type { ChatbotQuestion } from "./types"

const CARD = "mx-4 my-2 ml-[3.75rem] max-w-xl rounded-lg border border-outline-gray-2 bg-surface-white"
interface ChatbotQuestionCardProps {
    chatId: string
    question: ChatbotQuestion
}

/** The AI's questions as one card. While open it is a shortcut (answer here, or just type in the chat); once answered or skipped it shrinks to a line. */
export const ChatbotQuestionCard = ({ chatId, question }: ChatbotQuestionCardProps) => {
    const asked: AskedQuestion[] = JSON.parse(question.questions)
    return question.status === "Pending" ? <OpenQuestions chatId={chatId} question={question} asked={asked} /> : <ClosedQuestions question={question} asked={asked} />
}

/** The arrows between questions, with a dot for each: filled when it has an answer, ringed when it is the one shown. */
const QuestionArrows = ({ count, current, answered, onGo }: { count: number; current: number; answered: boolean[]; onGo: (index: number) => void }) => (
    <div className="flex shrink-0 items-center gap-1">
        <Button size="xs" variant="ghost" isIconButton aria-label={_("Previous question")} disabled={current === 0} onClick={() => onGo(current - 1)}><ChevronLeftIcon /></Button>
        <span className="flex items-center gap-1" aria-label={`${current + 1}/${count}`}>
            {Array.from({ length: count }, (_unused, index) => (
                <span key={index} className={cn("size-2 rounded-full border border-outline-gray-3", answered[index] && "bg-surface-gray-6", index === current && "ring-2 ring-outline-gray-4")} />
            ))}
        </span>
        <Button size="xs" variant="ghost" isIconButton aria-label={_("Next question")} disabled={current === count - 1} onClick={() => onGo(current + 1)}><ChevronRightIcon /></Button>
    </div>
)

const OpenQuestions = ({ chatId, question, asked }: ChatbotQuestionCardProps & { asked: AskedQuestion[] }) => {
    const { answer, busy } = useAnswerChatbotQuestion(chatId)
    const [drafts, setDrafts] = useState<Draft[]>(() => asked.map(() => emptyDraft))
    const [current, setCurrent] = useState(0)
    const answers = allAnswers(asked, drafts)
    const item = asked[current]
    const update = (change: (draft: Draft) => Draft) => setDrafts((previous) => previous.map((draft, other) => (other === current ? change(draft) : draft)))

    return (
        <div className={`${CARD} flex flex-col gap-3 p-3`}>
            {/* Keyed by question, so each keeps its own open "Other…" box. */}
            <div key={item.question} className="flex flex-col gap-2">
                <QuestionHeading text={item.question}>
                    {asked.length > 1 && <QuestionArrows count={asked.length} current={current} answered={answers.map(Boolean)} onGo={setCurrent} />}
                </QuestionHeading>
                <ChatbotQuestionItem item={item} draft={drafts[current]} busy={busy} onChange={update}
                    onPicked={asked.length > 1 ? () => setCurrent(nextToAnswer(asked, drafts, current)) : undefined} />
            </div>
            <div className="flex items-center gap-2">
                <Button size="sm" disabled={busy || !hasAnyAnswer(asked, drafts)} onClick={() => answer(question.name, answers)}>{_("Submit")}</Button>
                <span className="text-xs text-ink-gray-5">{_("Or just type your answer in the chat.")}</span>
            </div>
        </div>
    )
}

const ClosedQuestions = ({ question, asked }: { question: ChatbotQuestion; asked: AskedQuestion[] }) => {
    const [open, setOpen] = useState(false)
    const answered = question.status === "Answered"
    const answers: string[] = question.answers ? JSON.parse(question.answers) : []
    return (
        <div className={`${CARD} overflow-hidden`}>
            <button type="button" aria-expanded={open} onClick={() => setOpen((value) => !value)} className="flex w-full items-center gap-2 px-3 py-2 text-left text-p-sm hover:bg-surface-gray-1">
                {answered ? <CircleCheckIcon className="size-4 shrink-0 text-ink-green-8" /> : <CircleSlashIcon className="size-4 shrink-0 text-ink-gray-5" />}
                <span className="min-w-0 flex-1 truncate text-ink-gray-7">{asked[0]?.question}{asked.length > 1 ? ` (+${asked.length - 1})` : ""}</span>
                <Badge variant="subtle" theme={answered ? "green" : "gray"}>{answered ? _("Answered") : _("Skipped")}</Badge>
                {open ? <ChevronDownIcon className="size-4 shrink-0" /> : <ChevronRightIcon className="size-4 shrink-0" />}
            </button>
            {open && (
                <div className="flex flex-col gap-2 border-t border-outline-gray-2 p-3">
                    {asked.map((item, index) => (
                        <div key={item.question} className="flex flex-col gap-0.5 text-p-sm">
                            <span className="text-ink-gray-5">{item.question}</span>
                            <span className="font-medium text-ink-gray-8">{answers[index] || (answered ? _("(not answered)") : "—")}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
