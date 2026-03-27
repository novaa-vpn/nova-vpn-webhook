import { supabase } from "../lib/supabase"

export default async function handler(req, res) {

const { chat_id } = req.query

if (!chat_id) {
  return res.status(400).json({ error: "chat_id required" })
}

// گرفتن کاربر
const { data, error } = await supabase
  .from("users")
  .select("*")
  .eq("chat_id", chat_id)
  .maybeSingle()

// اگر خطای واقعی بود
if (error) {
  return res.status(500).json({ error: error.message })
}

// اگر کاربر وجود ندارد → بساز
if (data === null) {

  const { data: newUser, error: insertError } = await supabase
    .from("users")
    .insert({
      chat_id: chat_id,
      balance: 0,
      role: "user"
    })
    .select()
    .single()

  if (insertError) {
    return res.status(500).json({ error: insertError.message })
  }

  return res.json(newUser)
}

// اگر وجود دارد
return res.json(data)

}
