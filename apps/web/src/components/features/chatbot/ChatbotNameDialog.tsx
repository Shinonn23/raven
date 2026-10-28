import { useState } from "react"
import { FolderIcon, LightbulbIcon } from "lucide-react"
import { Dialog, DialogClose, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@components/ui/dialog"
import { Input } from "@components/ui/input"
import { Label } from "@components/ui/label"
import { Button } from "@components/ui/button"
import _ from "@lib/translate"

interface ChatbotNameDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    title: string
    label: string
    submitLabel: string
    initialName?: string
    placeholder?: string
    hint?: string
    onSubmit: (name: string) => Promise<unknown> | void
}

/** One name prompt for "Create project" and "Rename chat". */
export const ChatbotNameDialog = (props: ChatbotNameDialogProps) => (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
        <DialogContent className="sm:max-w-[480px]">
            {/* Gated on open so the field starts fresh every time. */}
            {props.open && <ChatbotNameForm {...props} />}
        </DialogContent>
    </Dialog>
)

const ChatbotNameForm = ({ title, label, submitLabel, initialName = "", placeholder, hint, onSubmit, onOpenChange }: ChatbotNameDialogProps) => {
    const [name, setName] = useState(initialName)
    const [isSubmitting, setIsSubmitting] = useState(false)

    const submit = async (event: React.FormEvent) => {
        event.preventDefault()
        setIsSubmitting(true)
        try {
            await onSubmit(name.trim())
            onOpenChange(false)
        } finally {
            setIsSubmitting(false)
        }
    }

    return (
        <form onSubmit={submit} className="flex flex-col gap-4">
            <DialogHeader>
                <DialogTitle>{title}</DialogTitle>
            </DialogHeader>
            <div className="flex flex-col gap-1.5">
                <Label htmlFor="chatbot-name">{label}</Label>
                <div className="relative">
                    <FolderIcon className="pointer-events-none absolute start-3 top-1/2 size-4 -translate-y-1/2 text-ink-gray-5" />
                    <Input id="chatbot-name" autoFocus maxLength={140} className="ps-9" value={name} placeholder={placeholder} onChange={(event) => setName(event.target.value)} />
                </div>
            </div>
            {hint && (
                <div className="flex items-start gap-2 rounded-lg bg-surface-gray-2 p-3 text-p-sm text-ink-gray-6">
                    <LightbulbIcon className="mt-0.5 size-4 shrink-0" />
                    <span>{hint}</span>
                </div>
            )}
            <DialogFooter>
                <DialogClose asChild>
                    <Button size="md" type="button" variant="outline">{_("Cancel")}</Button>
                </DialogClose>
                <Button size="md" type="submit" disabled={!name.trim()} loading={isSubmitting}>{submitLabel}</Button>
            </DialogFooter>
        </form>
    )
}
