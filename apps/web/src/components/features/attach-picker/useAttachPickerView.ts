import { useLocalStorage } from "usehooks-ts"
import { siteKey } from "@lib/site"
import type { PickerView } from "./types"

/** The view (list / cards / large cards) the user last chose, remembered across dialogs and sessions. */
export const useAttachPickerView = () => useLocalStorage<PickerView>(siteKey("attach-picker-view"), "list")
