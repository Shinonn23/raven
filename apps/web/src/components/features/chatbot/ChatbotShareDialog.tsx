import { useState } from "react"
import { XIcon } from "lucide-react"
import { UserPicker } from "@components/common/UserFormField"
import { Button } from "@components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@components/ui/dialog"
import { errorResponseToast } from "@components/ui/error-banner"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@components/ui/select"
import { useUser } from "@hooks/useUser"
import _ from "@lib/translate"
import { useChatbotShares } from "./useChatbotChat"
import type { ChatbotShare } from "./types"

const ShareRow = ({ share, onRemove }: { share: ChatbotShare; onRemove: () => void }) => {
    const user = useUser(share.user)
    return (
        <div className="flex items-center gap-2 py-1.5 text-sm">
            <span className="min-w-0 flex-1 truncate text-ink-gray-8">{user?.full_name || share.user}</span>
            <span className="text-xs text-ink-gray-5">{share.write ? _("Can edit") : _("Can view")}</span>
            <Button variant="ghost" size="sm" isIconButton aria-label={_("Remove access")} onClick={onRemove}><XIcon /></Button>
        </div>
    )
}

const ShareForm = ({ chatId }: { chatId: string }) => {
    const { shares, share, unshare } = useChatbotShares(chatId, true)
    const [recipient, setRecipient] = useState("")
    const [canWrite, setCanWrite] = useState("view")
    const [isSharing, setIsSharing] = useState(false)

    const submit = async () => {
        setIsSharing(true)
        try {
            await share(recipient, canWrite === "edit")
            setRecipient("")
        } catch (error) {
            errorResponseToast(_("Could not share this chat"), error as never)
        } finally {
            setIsSharing(false)
        }
    }

    return (
        <>
            <div className="flex items-center gap-2">
                <div className="min-w-0 flex-1"><UserPicker value={recipient} onChange={setRecipient} placeholder={_("Add people")} /></div>
                <Select value={canWrite} onValueChange={setCanWrite}>
                    <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
                    <SelectContent>
                        <SelectItem value="view">{_("Can view")}</SelectItem>
                        <SelectItem value="edit">{_("Can edit")}</SelectItem>
                    </SelectContent>
                </Select>
                <Button disabled={!recipient} loading={isSharing} onClick={submit}>{_("Share")}</Button>
            </div>
            <div className="flex flex-col divide-y">
                {shares.length === 0 && <p className="py-2 text-p-sm text-ink-gray-5">{_("Only you can see this chat.")}</p>}
                {shares.map((share) => <ShareRow key={share.user} share={share} onRemove={() => unshare(share.user)} />)}
            </div>
        </>
    )
}

/** Owner-only dialog: give other people access to a chat, or take it back. */
export const ChatbotShareDialog = ({ chatId, open, onOpenChange }: { chatId: string; open: boolean; onOpenChange: (open: boolean) => void }) => (
    <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-[520px]">
            <DialogHeader>
                <DialogTitle>{_("Share chat")}</DialogTitle>
                <DialogDescription>{_("People you add can read this conversation. Editors can also continue it.")}</DialogDescription>
            </DialogHeader>
            {open && <ShareForm chatId={chatId} />}
        </DialogContent>
    </Dialog>
)
