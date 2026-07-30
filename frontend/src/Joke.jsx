export default function Joke(prop){
    let flag = false
    return (
        <article>
            {flag && <h1>{prop.setup} </h1>}
            <p>{prop.punchline}</p>
        </article>
    )
}
