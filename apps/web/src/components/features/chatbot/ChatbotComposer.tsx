import { useRef, useState, type KeyboardEvent } from "react"
import { useAtom } from "jotai"
import { BoldIcon, CodeIcon, ItalicIcon, ListIcon, QuoteIcon, SendHorizontalIcon, TypeIcon } from "lucide-react"
import AttachFrappeDocumentDialog, { LinkedDocumentBanner } from "@components/features/ChatInput/AttachFrappeDocumentDialog"
import { Button } from "@components/ui/button"
import { Separator } from "@components/ui/separator"
import { linkedDocumentAtom } from "@utils/channelAtoms"
import { cn } from "@lib/utils"
import _ from "@lib/translate"
import { AttachFileButton } from "../attach-picker/AttachFileButton"
import { useChatbotFiles } from "./useChatbotFiles"
import { ChatbotAttachmentCard } from "./ChatbotAttachmentCard"
import { ChatbotModelPicker } from "./ChatbotModelPicker"
import { useChatbotChoice } from "./useChatbotChoice"
import { ChatbotSlashMenu } from "./ChatbotSlashMenu"
import { applyMarkdownFormat, matchingSkills, slashQuery, type MarkdownFormat } from "./markdownFormatting"
import { useChatbotSkills, useRecommendedDocuments } from "./useChatbotComposerData"
import type { ChatbotOutgoingMessage, ChatbotSkill } from "./types"

const FORMAT_BUTTONS: { format: MarkdownFormat; label: string; Icon: typeof BoldIcon }[] = [
    { format: "bold", label: "Bold", Icon: BoldIcon },
    { format: "italic", label: "Italic", Icon: ItalicIcon },
    { format: "code", label: "Code", Icon: CodeIcon },
    { format: "list", label: "List", Icon: ListIcon },
    { format: "quote", label: "Quote", Icon: QuoteIcon },
]

interface ChatbotComposerProps {
    onSend: (message: ChatbotOutgoingMessage) => void
    disabled?: boolean
    /** Scopes the staged document, so each chat keeps its own draft attachment. */
    draftKey: string
}

/** Prompt box: formatting, "/" skills, system files, system documents. Enter sends, Shift+Enter adds a line. */
export const ChatbotComposer = ({ onSend, disabled, draftKey }: ChatbotComposerProps) => {
    const [text, setText] = useState("")
    const { files, addUploads, addSystemFiles, remove: removeFile, clear: clearFiles } = useChatbotFiles()
    const [showFormatting, setShowFormatting] = useState(false)
    const [slashIndex, setSlashIndex] = useState(0)
    const [document, setDocument] = useAtom(linkedDocumentAtom(draftKey))
    const textarea = useRef<HTMLTextAreaElement>(null)
    const skills = useChatbotSkills()
    const recommended = useRecommendedDocuments()
    const { choice } = useChatbotChoice()

    const query = slashQuery(text)
    const slashMatches = query === null ? [] : matchingSkills(skills, query)
    const hasContent = text.trim().length > 0 || files.length > 0 || document !== null
    const canSend = hasContent && !disabled

    const send = () => {
        if (!canSend) return
        onSend({ text: text.trim(), files, document, model: choice?.model, effort: choice?.effort })
        setText("")
        clearFiles()
        setDocument(null)
    }

    const pickSkill = (skill: ChatbotSkill) => {
        setText(skill.prompt)
        setSlashIndex(0)
        textarea.current?.focus()
    }

    const format = (kind: MarkdownFormat) => {
        const field = textarea.current
        if (!field) return
        const edit = applyMarkdownFormat({ value: text, selectionStart: field.selectionStart, selectionEnd: field.selectionEnd }, kind)
        setText(edit.value)
        requestAnimationFrame(() => { field.focus(); field.setSelectionRange(edit.selectionStart, edit.selectionEnd) })
    }

    const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
        if (event.nativeEvent.isComposing) return
        if (query !== null && slashMatches.length > 0) {
            if (event.key === "ArrowDown" || event.key === "ArrowUp") {
                event.preventDefault()
                const step = event.key === "ArrowDown" ? 1 : -1
                setSlashIndex((index) => (index + step + slashMatches.length) % slashMatches.length)
                return
            }
            if (event.key === "Enter" || event.key === "Tab") {
                event.preventDefault()
                pickSkill(slashMatches[Math.min(slashIndex, slashMatches.length - 1)])
                return
            }
        }
        if (event.key !== "Enter" || event.shiftKey) return
        event.preventDefault()
        send()
    }

    return (
        <div className="relative w-full">
            {query !== null && <ChatbotSlashMenu skills={slashMatches} activeIndex={slashIndex} onPick={pickSkill} />}
            <div className="w-full overflow-y-hidden border-outline-gray-2 bg-surface-base shadow-outline-base focus-within:border-outline-gray-3 md:rounded-lg md:border">
                {showFormatting && (
                    <div className="flex items-center gap-0.5 border-b border-outline-gray-2 px-1 py-1">
                        {FORMAT_BUTTONS.map(({ format: kind, label, Icon }) => (
                            <Button key={kind} type="button" variant="ghost" size="sm" isIconButton aria-label={_(label)} title={_(label)} onClick={() => format(kind)}><Icon /></Button>
                        ))}
                    </div>
                )}
                <LinkedDocumentBanner channelID={draftKey} />
                {files.length > 0 && (
                    <div className="flex flex-wrap gap-2 px-3 pt-3">
                        {files.map((file) => <ChatbotAttachmentCard key={file.file_url} file={file} className="h-28 w-28" onRemove={() => removeFile(file)} />)}
                    </div>
                )}
                <textarea
                    ref={textarea}
                    autoFocus
                    rows={1}
                    value={text}
                    onChange={(event) => { setText(event.target.value); setSlashIndex(0) }}
                    onKeyDown={onKeyDown}
                    placeholder={_("Type a message...")}
                    aria-label={_("Message")}
                    className="block max-h-64 min-h-14 w-full resize-none bg-transparent px-3 py-2 text-p-base text-ink-gray-8 outline-none field-sizing-content placeholder:text-ink-gray-4 md:min-h-16"
                />
                <div className="flex items-center gap-1 px-1 pb-1">
                    <AttachFileButton
                        onUploadFiles={addUploads}
                        onPickSystemFiles={addSystemFiles}
                        documents={recommended}
                        onPickDocument={(picked) => setDocument(picked)}
                    />
                    <Button type="button" variant="ghost" size="sm" isIconButton aria-label={_("Formatting")} aria-pressed={showFormatting}
                        className={cn(showFormatting && "bg-surface-gray-3 text-ink-gray-9")} onClick={() => setShowFormatting((visible) => !visible)}>
                        <TypeIcon />
                    </Button>
                    <Separator orientation="vertical" className="mx-1 h-4!" />
                    <AttachFrappeDocumentDialog channelID={draftKey} recommended={recommended} />
                    <div className="flex-1" />
                    <ChatbotModelPicker />
                    <Button size="sm" disabled={!canSend} onClick={send}><SendHorizontalIcon />{_("Send")}</Button>
                </div>
            </div>
        </div>
    )
}
