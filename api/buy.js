import { supabase } from "../lib/supabase"

export default async function handler(req,res){

const { chat_id, plan } = req.body

if(!chat_id || !plan)
return res.status(400).json({error:"missing data"})

await supabase.from("orders").insert({
  chat_id,
  plan,
  status:"pending"
})

res.json({ok:true})

}
