import { supabase } from "../lib/supabase"

export default async function handler(req,res){

const { chat_id } = req.query

if(!chat_id)
return res.status(400).json({error:"chat_id required"})

const { data, error } = await supabase
.from("users")
.select("*")
.eq("chat_id",chat_id)
.single()

if(error) return res.status(500).json({error:error.message})

res.json(data)

}
