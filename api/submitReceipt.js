import { supabase } from "../lib/supabase"

export default async function handler(req,res){

const { chat_id, image } = req.body

if(!chat_id || !image)
return res.status(400).json({error:"missing data"})

await supabase.from("receipts").insert({
  chat_id,
  image,
  status:"pending"
})

res.json({ok:true})

}
