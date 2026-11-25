uniform int u_part;
uniform sampler2D u_reflect;
uniform float u_reflOn;
uniform float u_light[32];     // x, z, intensite, teinte : feux des vehicules proches
in vec3 v_pos; in vec2 v_p; in vec3 v_n;
out vec4 frag;

float aaLine(float d, float w){ float f = fwidth(d); return smoothstep(w+f, w-f*.5, abs(d)) ; }

void main(){
    vec3 cp = u_cam.xyz; cp.y *= u_track.w;
    vec3 view = v_pos - cp; float dist = length(view); vec3 v = -view/dist;
    float s = u_track.x + v_pos.z;
    vec3 n = normalize(v_n);
    float night = 1. - .86*u_sun.w;
    vec3 L = normalize(u_sun.xyz);
    vec3 alb = vec3(.03), emi = vec3(0.);
    float wet = u_gnd.w, reflK = 0., x = v_pos.x;
    vec2 sp = vec2(x, s);
    if(u_part==0 || u_part==4){
        float half_w = u_head.w;
        float det = smoothstep(60.,6.,dist);
        float gr = mix(.5, noise(sp*vec2(34.,30.)), det)*.5 + fbm(sp*vec2(.9,.10))*.5;
        float tire = 0.;
        for(int i=0;i<4;i++){ float lx = -5.4 + 3.6*float(i); tire += exp(-pow((abs(x-lx)-.85)*2.6,2.)); }
        vec3 base = ENV==1 ? vec3(.085,.060,.052) : ENV==3 ? vec3(.065,.068,.075) : vec3(.030,.032,.042);
        alb = base * (.62 + .75*gr) * (1. - .22*tire);
        float puddle = smoothstep(.46,.66, fbm(sp*vec2(.17,.045)+7.)) * wet;
        float w_all = clamp(wet*.55 + puddle*.6, 0., 1.);
        alb *= 1. - .45*w_all;
        if(u_part==0){
            float fade = 1.;
            float mk = 0.;
            for(int i=-1;i<=1;i++){
                float ln = aaLine(x - 3.6*float(i), .075);
                float dsh = smoothstep(.0,.04, fract(s/12.)) * smoothstep(.40,.36, fract(s/12.));
                mk = max(mk, ln*dsh);
            }
            mk = max(mk, aaLine(abs(x)-7.25, .085));
            vec3 mc = ENV==1 ? vec3(.85,.62,.22) : vec3(.80,.84,.90);
            alb = mix(alb, mc*.75, mk*(.72+.28*gr));
            emi += mc * mk * (ENV==3||ENV==1 ? .015 : .075);
            // liseres lumineux d'accotement
            float eg = abs(x) - (half_w - .28);
            vec3 ec = x < 0. ? u_edge.rgb : u_edge2.rgb;
            float pulse = .75 + .25*sin(s*.10 - u_cam.w*6.);
            float on = ENV==3 ? .22 : ENV==1 ? .45 : 1.;
            emi += ec * aaLine(eg, .055) * 1.7 * pulse * on;
            emi += ec * exp(-abs(eg)*2.4) * .085 * on;
            if(ENV==4){ float ch = fract(s/20. - abs(x)*.05 - u_cam.w*.0); emi += mix(u_edge.rgb,u_edge2.rgb,.5)*smoothstep(.02,.0,abs(ch-.5))*.35*step(abs(x),7.25); }
            // reflecteurs de chaussee
            vec2 cat = vec2(abs(mod(x+1.8,3.6)-1.8+0.)*1., fract(s/12.)*12.-8.4);
            float cx = min(min(abs(x),abs(x-3.6)),abs(x+3.6));
            emi += vec3(.75,.85,1.) * smoothstep(.07,.02,cx)*smoothstep(.10,.03,abs(cat.y)) * (.25 + 2.5*headBeam(v_pos)*u_head.y);
        } else {
            vec2 g = abs(fract(v_pos.xz/1.2)-.5);
            float gl = smoothstep(.492,.499,max(g.x,g.y));
            float r = length(v_pos.xz);
            alb = vec3(.012,.014,.022);
            emi += vec3(.0,.35,.45)*gl*.10*exp(-r*.16);
            emi += u_acc.rgb * smoothstep(.030,.0,abs(r-3.35)) * 1.5;
            emi += u_acc.rgb * smoothstep(.012,.0,abs(r-3.62)) * .8 * step(.5, fract(atan(v_pos.x,v_pos.z)*14./PI + u_cam.w*.15));
            emi += u_acc.rgb * exp(-abs(r-3.35)*2.6)*.07;
            w_all = .85; puddle = .7;
        }
        // lumieres
        vec3 hemi = u_sky.rgb*1.2;
        float nl = max(L.y,0.);
        vec3 lamp = lampLight(v_pos, s);
        vec3 light = (u_suncol.rgb*nl*.9 + hemi + lamp*1.35)*night;
        light += vec3(.85,.93,1.05)*headBeam(v_pos)*u_head.y*(1.5+2.6*u_sun.w);
        vec3 col = alb*light;
        col += lamp*.020*night*(1.+2.*w_all);
        col += vec3(.85,.93,1.05)*headBeam(v_pos)*u_head.y*.018*(1.+2.*u_sun.w);
        // halos des feux des autres vehicules
        for(int i=0;i<8;i++){
            float k = u_light[i*4+2];
            if(k <= 0.) continue;
            vec2 q = vec2(x - u_light[i*4], v_pos.z - u_light[i*4+1]);
            float hue = u_light[i*4+3];
            q.y = q.y > 0. ? q.y*1.6 : q.y*.55;
            col += (hue < .5 ? vec3(1.,.05,.08) : u_acc.rgb) * k * exp(-dot(q,q)*.26) * .10;
        }
        // reflet planaire deforme
        float fr = pow(1.-max(v.y,0.), 3.5);
        vec2 uv = gl_FragCoord.xy / u_res.xy;
        vec2 wob = vec2(noise(sp*vec2(1.9,.75))-.5, noise(sp*vec2(1.6,.95)+31.)-.5);
        if(ENV==2){ vec2 rp = sp*1.6; vec2 id=floor(rp); vec2 f=fract(rp)-.5; float ph=fract(u_cam.w*1.4+hash21(id)); float rr=length(f-(hash22(id)-.5)*.4);
            wob += normalize(f+.001)*smoothstep(.06,.0,abs(rr-ph*.5))*(1.-ph)*1.4*smoothstep(45.,8.,dist); }
        float amt = (.12 + .88*fr) * w_all;
        if(u_reflOn > .5){
            float rgh = mix(.011, .0028, puddle) * (u_part==4 ? .35 : 1.);
            vec3 r = texture(u_reflect, uv + wob*rgh*vec2(1.,2.2)).rgb*.5;
            r += texture(u_reflect, uv + wob.yx*rgh*vec2(-1.2,3.0) + vec2(0.,-.006)).rgb*.3;
            r += texture(u_reflect, uv - wob*rgh*vec2(.6,4.2) + vec2(0.,-.014)).rgb*.2;
            col = mix(col, r, clamp(amt*.85,0.,.9));
        } else {
            vec3 rd = reflect(-v, normalize(vec3(wob.x*.12,1.,wob.y*.12)));
            col = mix(col, skyBase(vec3(rd.x,abs(rd.y),rd.z))*.8, clamp(amt*.7,0.,.9));
        }
        col += emi;
        if(u_part==4) col = mix(col, skyBase(vec3(-v.x,.0,-v.z)), smoothstep(9.,24.,length(v_pos.xz)));
        else col = applyFog(col, dist, -v);
        frag = vec4(col,1.);
        return;
    }
    if(u_part==1){
        float slope = 1.-n.y;
        float k = fbm(v_pos.xz*vec2(.0,0.)+sp*.25);
        if(ENV==1){ alb = mix(vec3(.46,.235,.125), vec3(.60,.34,.18), k);
            alb *= .86+.14*sin((sp.x*.9+sp.y*.35+k*5.)*3.2)*smoothstep(55.,10.,dist);
            alb = mix(alb, vec3(.28,.11,.07), smoothstep(.22,.5,slope)); }
        else if(ENV==3){ alb = mix(vec3(.060,.105,.045), vec3(.12,.135,.06), k);
            alb = mix(alb, vec3(.16,.155,.15)*(.6+.7*k), smoothstep(.22,.42,slope));
            alb = mix(alb, vec3(.75,.80,.88), smoothstep(38.,60.,v_pos.y+k*14.)*step(x,0.)*smoothstep(.75,.35,slope));
            alb = mix(alb, vec3(.14,.13,.11), smoothstep(2.5,0.,abs(x)-9.)); }
        else { alb = vec3(.018,.019,.028)*(.6+k*.8);
            vec2 g = abs(fract(sp/4.)-.5); emi += u_edge.rgb*.018*smoothstep(.485,.5,max(g.x,g.y))*smoothstep(90.,10.,dist); }
        vec3 hemi = mix(u_gnd.rgb,u_sky.rgb,n.y*.5+.5);
        vec3 light = (u_suncol.rgb*max(dot(n,L),0.) + hemi*1.15 + lampLight(v_pos,s)*.7)*night + vec3(.85,.93,1.05)*headBeam(v_pos)*u_head.y*(1.+2.*u_sun.w);
        frag = vec4(applyFog(alb*light+emi, dist, -v), 1.);
        return;
    }
    if(u_part==2){
        float y = v_pos.y; float seg = fract(s/4.);
        alb = ENV==1 ? vec3(.30,.18,.13) : ENV==3 ? vec3(.34,.36,.39) : vec3(.045,.048,.062);
        alb *= .75 + .25*noise(vec2(s*1.3,y*9.)) ;
        alb *= 1. - .55*smoothstep(.018,.0,abs(seg-.5)-.004);
        if(ENV==3) alb *= .55+.45*abs(sin(y*21.));
        vec3 ec = x < 0. ? u_edge.rgb : u_edge2.rgb;
        float on = ENV==3 ? .10 : ENV==1 ? .16 : 1.;
        float run = .55 + .9*smoothstep(.80,1.,sin(s*.16 - u_cam.w*9.)*.5+.5);
        emi += ec * smoothstep(.055,.030,abs(y-.60)) * 1.9*on*run;
        emi += ec * smoothstep(.30,.0,abs(y-.60)) * .05*on;
        float rf = smoothstep(.10,.06,abs(y-.36))*smoothstep(.06,.04,abs(seg-.1));
        emi += vec3(1.,.5,.1)*rf*(.10+2.*headBeam(v_pos)*u_head.y);
        vec3 hemi = mix(u_gnd.rgb,u_sky.rgb,n.y*.5+.5);
        vec3 light = (u_suncol.rgb*max(dot(n,L),0.) + hemi + lampLight(v_pos,s)*1.1)*night + vec3(.85,.93,1.05)*headBeam(v_pos)*u_head.y*1.3*(1.+2.*u_sun.w);
        frag = vec4(applyFog(alb*light+emi, dist, -v), 1.);
        return;
    }
    // tunnel
    float a = v_p.x;                       // 0..1 de gauche a droite
    float ring = fract(s/10.); float rid = floor(s/10.);
    float pan = fract(a*14.);
    alb = vec3(.050,.052,.070)*(.7+.5*hash21(vec2(floor(a*14.), floor(s/5.))));
    alb *= 1.-.7*smoothstep(.04,.0,abs(pan-.5)-.46+.02) ;
    alb *= 1.-.6*smoothstep(.02,.0,abs(fract(s/5.)-.5)-.49+.01);
    vec3 c1 = u_edge.rgb, c2 = u_edge2.rgb;
    float wave = smoothstep(.55,1., sin(s*.045 - u_cam.w*3.2)*.5+.5);
    float rr = smoothstep(.035,.018,abs(ring-.5));
    emi += mix(c1,c2,step(.5,hash11(rid))) * rr * (.30 + 1.5*wave);
    float strip = smoothstep(.010,.005,abs(a-.5)) + .6*smoothstep(.006,.003,abs(abs(a-.5)-.22));
    emi += mix(c2,c1,smoothstep(.2,.8,fract(s*.01))) * strip * (.7+.45*sin(s*.35 - u_cam.w*16.));
    float hol = step(.82, hash21(vec2(floor(a*14.), rid)))*step(.15,pan)*step(pan,.85)*step(.15,ring)*step(ring,.42);
    emi += mix(c1,vec3(1.,.2,.35),step(.75,hash11(rid*3.3)))*hol*(.25+.5*step(.5,fract(v_pos.y*3.+u_cam.w*2.)));
    vec3 glow = mix(c1,c2,step(.5,hash11(rid)))*exp(-abs(ring-.5)*9.)*(.04+.16*wave);
    vec3 light = u_sky.rgb*1.2*night + lampLight(v_pos,s)*.6*night + vec3(.85,.93,1.05)*headBeam(v_pos)*u_head.y*1.2;
    frag = vec4(applyFog(alb*light + glow*.35 + emi*mix(1.,.35,u_sun.w), dist, -v), 1.);
}
